package kafk

import (
	"context"
	"encoding/json"
	"example.com/bot_worker/internal/processor"
	"example.com/bot_worker/pkg/config"
	"example.com/bot_worker/pkg/models"
	"example.com/bot_worker/pkg/tools"
	"fmt"
	"log/slog"
	"sync"
	"time"

	"github.com/IBM/sarama"
)

type KafkaConsumer struct {
	proc *processor.Processor

	topic   []string
	brokers []string

	consumer sarama.ConsumerGroup
	producer *KafkaProducer
	handler  *ConsumerGroupHandler

	running bool
	mu      *sync.Mutex
	wg      *sync.WaitGroup
	ctx     context.Context
	cancel  context.CancelFunc

	logger *slog.Logger
}

// ConsumerGroupHandler для групп, реализует интерфейс sarama.ConsumerGroupHandler
type ConsumerGroupHandler struct {
	proc     *processor.Processor
	producer *KafkaProducer
	consumer *KafkaConsumer
	logger   *slog.Logger
}

func NewKafkaConsumer(ctx context.Context, brokers []string, producer *KafkaProducer,
	proc *processor.Processor, logger *slog.Logger) (*KafkaConsumer, error) {

	var cfg = ctx.Value("config").(*config.Configuration)

	configSarama := sarama.NewConfig()
	configSarama.Consumer.Offsets.Initial = sarama.OffsetNewest
	configSarama.Consumer.Offsets.AutoCommit.Enable = false
	configSarama.Consumer.MaxProcessingTime = 300 * time.Millisecond
	configSarama.Consumer.Group.Session.Timeout = 6 * time.Second
	configSarama.Consumer.Group.Heartbeat.Interval = 2 * time.Second
	configSarama.Consumer.MaxProcessingTime = 1 * time.Second
	configSarama.ClientID = cfg.KafkaConsumerClientID
	configSarama.Version = sarama.V2_6_0_0

	consumer, err := sarama.NewConsumerGroup(brokers, cfg.KafkaConsumerGroup, configSarama)
	if err != nil {
		return nil, fmt.Errorf("error creating Kafka consumer group: %w", err)
	}

	ctx, cancel := context.WithCancel(ctx)

	kc := &KafkaConsumer{
		consumer: consumer,
		topic:    cfg.KafkaConsumerTopics,
		producer: producer,
		running:  false,
		brokers:  brokers,
		mu:       new(sync.Mutex),
		wg:       new(sync.WaitGroup),
		ctx:      ctx,
		cancel:   cancel,
		proc:     proc,
		logger:   logger,
	}

	kc.handler = &ConsumerGroupHandler{
		proc:     proc,
		producer: producer,
		consumer: kc,
		logger:   logger,
	}

	return kc, nil
}

func (rc *KafkaConsumer) Start() error {
	rc.mu.Lock()
	defer rc.mu.Unlock()

	if rc.running {
		return nil
	}

	rc.running = true
	rc.wg.Add(1)
	go rc.consume()

	return nil
}

// consume запускает consumer group
func (rc *KafkaConsumer) consume() {
	defer rc.wg.Done()

	for rc.isRunning() {
		select {
		case <-rc.ctx.Done():
			return
		default:
		}

		err := rc.consumer.Consume(rc.ctx, rc.topic, rc.handler)
		if err != nil {
			rc.logger.Warn("consumer",
				"error", err,
				"place", tools.GetPlace())

			select {
			case <-rc.ctx.Done():
				return
			case <-time.After(5 * time.Second):
			}
		}
	}
}

// isRunning - проверяет, работает ли консюмер
func (rc *KafkaConsumer) isRunning() bool {
	rc.mu.Lock()
	defer rc.mu.Unlock()
	return rc.running
}

// Stop останавливает консюмера
func (rc *KafkaConsumer) Stop() error {
	rc.mu.Lock()
	if !rc.running {
		rc.mu.Unlock()
		return nil
	}
	rc.running = false
	rc.mu.Unlock()

	rc.cancel()
	rc.wg.Wait()

	if err := rc.consumer.Close(); err != nil {
		rc.logger.Error("consumer close",
			"error", err,
			"place", tools.GetPlace())

		return fmt.Errorf("kafka consumer close error: %w", err)
	}
	rc.logger.Info(tools.ServiceName,
		"consumer stop", "success",
		"place", tools.GetPlace())

	return nil
}

// Setup - вызывается перед началом потребления
func (h *ConsumerGroupHandler) Setup(_ sarama.ConsumerGroupSession) error {
	return nil
}

// Cleanup - вызывается после завершения потребления
func (h *ConsumerGroupHandler) Cleanup(_ sarama.ConsumerGroupSession) error {
	return nil
}

// ConsumeClaim - основной метод обработки сообщений
func (h *ConsumerGroupHandler) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	for message := range claim.Messages() {
		h.processMessage(session, message)
	}
	return nil
}

// processMessage обрабатывает одно сообщение
func (h *ConsumerGroupHandler) processMessage(session sarama.ConsumerGroupSession, msg *sarama.ConsumerMessage) {
	h.logger.Info("consumer",
		"pending request key", msg.Key,
		"place", tools.GetPlace())

	var req models.Request
	if err := json.Unmarshal(msg.Value, &req); err != nil {
		h.logger.Error("unmarshal message failed",
			"error", err,
			"place", tools.GetPlace())

		h.sendErrorResponse("invalid format json", msg)
		session.MarkMessage(msg, "")
		return
	}

	// Обрабатываем запрос
	response, err := h.handleRequest(req)
	if err != nil {
		h.logger.Warn("handle request failed",
			"error", err,
			"place", tools.GetPlace())

		// даже если ошибка, мы выдаем, потом сервис б в кафку обратно пришлет
	}
	// Отправляем ответ
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err = h.producer.SendResponse(ctx, response); err != nil {
		h.logger.Error("send response failed",
			"error", err,
			"place", tools.GetPlace())

		// Не коммитим, чтобы повторить позже
		return
	}

	// Коммитим сообщение после успешной обработки
	session.MarkMessage(msg, "")
	h.logger.Info("message sent",
		"status", "success",
		"place", tools.GetPlace())

}

// handleRequest вызывает сервис для обработки запроса
func (h *ConsumerGroupHandler) handleRequest(req models.Request) (models.Response, error) {
	var resp models.Response
	resp.Request = req
	resp.UserID = req.UserID
	resp.Attempt = req.Attempt
	resp.ChatID = req.ChatID

	response, metrics, err := h.proc.Process(&models.ProcessRequest{
		FilePath:   req.FileURL,
		Prompt:     req.Prompt,
		FileFormat: req.FileFormat,
	})
	resp.Metrics = metrics
	resp.Success = true

	if err != nil {
		resp.Success = false
		resp.Error = err.Error()
	}
	if response == nil {
		resp.Explanation = ""
		resp.Diagram = ""
		return resp, nil
	}
	resp.Explanation = response.Explanation
	resp.Diagram = response.Diagram
	return resp, nil
}

// sendErrorResponse отправляет ответ с ошибкой
func (h *ConsumerGroupHandler) sendErrorResponse(message string, _ *sarama.ConsumerMessage) {
	response := models.Response{
		Request:     models.Request{},
		UserID:      "",
		Success:     false,
		Error:       message,
		Explanation: "",
		Diagram:     "",
		Attempt:     -1,
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := h.producer.SendResponse(ctx, response); err != nil {
		h.logger.Warn("send response failed",
			"error", err,
			"place", tools.GetPlace())
	}
}
