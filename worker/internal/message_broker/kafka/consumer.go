package kafk

import (
	"context"
	"encoding/json"
	"example.com/bot_worker/internal/service"
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
	consumer sarama.ConsumerGroup
	topic    []string
	producer *KafkaProducer
	running  bool
	brokers  []string
	mu       *sync.Mutex
	wg       *sync.WaitGroup
	ctx      context.Context
	cancel   context.CancelFunc
	serv     service.ServiceInterface
	handler  *ConsumerGroupHandler
	logger   *slog.Logger
	logs     chan *models.Log
}

// ConsumerGroupHandler для групп, реализует интерфейс sarama.ConsumerGroupHandler
type ConsumerGroupHandler struct {
	serv     service.ServiceInterface
	producer *KafkaProducer
	consumer *KafkaConsumer
	logger   *slog.Logger
	logs     chan *models.Log
}

func NewKafkaConsumer(ctx context.Context, brokers []string, producer *KafkaProducer,
	serv service.ServiceInterface, logger *slog.Logger, logs chan *models.Log) (*KafkaConsumer, error) {

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
		serv:     serv,
		logs:     logs,
		logger:   logger,
	}

	kc.handler = &ConsumerGroupHandler{
		serv:     serv,
		producer: producer,
		consumer: kc,
		logger:   logger,
		logs:     logs,
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

		// Запускаем consumer group
		err := rc.consumer.Consume(rc.ctx, rc.topic, rc.handler)
		if err != nil {
			rc.logger.Warn(tools.ServiceName,
				"consume error", err,
				"place", tools.GetPlace())
			go func() {
				rc.logs <- tools.CreateLogStruct(tools.ServiceName, "warning", "kafka consumer",
					"consume", err.Error(), tools.GetPlace())
			}()

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
		rc.logger.Error(tools.ServiceName,
			"consumer close error", err,
			"place", tools.GetPlace())
		go func() {
			rc.logs <- tools.CreateLogStruct(tools.ServiceName, "error", "kafka consumer", "close",
				err.Error(), tools.GetPlace())
		}()
		return fmt.Errorf("kafka consumer close error: %w", err)
	}
	rc.logger.Info(tools.ServiceName,
		"consumer stop", "success",
		"place", tools.GetPlace())
	go func() {
		rc.logs <- tools.CreateLogStruct(tools.ServiceName, "info", "kafka consumer",
			"stop", "success", tools.GetPlace())
	}()
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
	h.logger.Info(tools.ServiceName,
		"pending request", string(msg.Value),
		"place", tools.GetPlace())
	go func() {
		h.logs <- tools.CreateLogStruct(tools.ServiceName, "info", "kafka consumer",
			"pending message", string(msg.Value), tools.GetPlace())
	}()

	var req models.Request
	if err := json.Unmarshal(msg.Value, &req); err != nil {
		h.logger.Error(tools.ServiceName,
			"unmarshal error", err,
			"place", tools.GetPlace())
		go func() {
			h.logs <- tools.CreateLogStruct(tools.ServiceName, "error", "kafka consumer",
				"unmarshal", err.Error(), tools.GetPlace())
		}()

		h.sendErrorResponse("invalid format json", msg)
		session.MarkMessage(msg, "")
		return
	}

	// Обрабатываем запрос
	response, err := h.handleRequest(req)
	if err != nil {
		h.logger.Warn(tools.ServiceName,
			"handle request error", err,
			"place", tools.GetPlace())

		go func() {
			h.logs <- tools.CreateLogStruct(tools.ServiceName, "warning", "kafka consumer",
				"handleRequest", err.Error(), tools.GetPlace())
		}()
		// return не делаем так как внутри success на false меняется и в кафку точно отправить надо это
	}

	// Отправляем ответ
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err = h.producer.SendResponse(ctx, response); err != nil {
		h.logger.Error(tools.ServiceName,
			"send response error", err,
			"place", tools.GetPlace())
		go func() {
			h.logs <- tools.CreateLogStruct(tools.ServiceName, "error", "kafka consumer", "send response",
				err.Error(), tools.GetPlace())
		}()

		// Не коммитим, чтобы повторить позже
		return
	}

	// Коммитим сообщение после успешной обработки
	session.MarkMessage(msg, "")
	h.logger.Info(tools.ServiceName,
		"process message", "success",
		"place", tools.GetPlace())

	go func() {
		data, _ := json.Marshal(response)
		h.logs <- tools.CreateLogStruct(tools.ServiceName, "info", "kafka consumer", "send message",
			string(data), tools.GetPlace())
	}()
}

// handleRequest вызывает сервис для обработки запроса
func (h *ConsumerGroupHandler) handleRequest(req models.Request) (models.Response, error) {
	var resp models.Response
	resp.TaskID = req.TaskID
	resp.UserID = req.UserID

	data, err := h.serv.Response(req.FileURL, req.Prompt)
	if err != nil {
		resp.Text = err.Error()
		resp.Success = false
		return resp, err
	}
	resp.Text = data
	resp.Success = true
	return resp, nil
}

// sendErrorResponse отправляет ответ с ошибкой
func (h *ConsumerGroupHandler) sendErrorResponse(message string, _ *sarama.ConsumerMessage) {
	response := models.Response{
		TaskID:  "unknown",
		UserID:  "unknown",
		Success: false,
		Text:    message,
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := h.producer.SendResponse(ctx, response); err != nil {
		h.logger.Warn(tools.ServiceName,
			"send response error", err,
			"place", tools.GetPlace())
		go func() {
			h.logs <- tools.CreateLogStruct(tools.ServiceName, "warning", "kafka consumer",
				"send response", err.Error(), tools.GetPlace())
		}()
	}
}
