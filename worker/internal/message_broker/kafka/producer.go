package kafk

import (
	"context"
	"encoding/json"
	"example.com/bot_worker/pkg/config"
	"example.com/bot_worker/pkg/models"
	"example.com/bot_worker/pkg/tools"
	"fmt"
	"log/slog"
	"time"

	"github.com/IBM/sarama"
)

type KafkaProducer struct {
	producer sarama.SyncProducer
	topic    string
	ctx      context.Context
}

func NewKafkaProducer(ctx context.Context, brokers []string) (*KafkaProducer, error) {
	var cfg = ctx.Value("config").(*config.Configuration)

	configSarama := sarama.NewConfig()
	configSarama.Producer.RequiredAcks = sarama.WaitForAll
	configSarama.Producer.Retry.Max = 10
	configSarama.Producer.Retry.Backoff = 100 * time.Millisecond
	configSarama.Producer.Flush.Bytes = 16384
	configSarama.Consumer.MaxProcessingTime = 1 * time.Second
	configSarama.Producer.Flush.Frequency = 5 * time.Millisecond
	configSarama.Producer.Return.Successes = true
	configSarama.ClientID = cfg.KafkaProducerClientID
	configSarama.Version = sarama.V2_6_0_0

	producer, err := sarama.NewSyncProducer(brokers, configSarama)
	if err != nil {
		return nil, fmt.Errorf("ошибка создания продьюсера: %w", err)
	}

	return &KafkaProducer{
		producer: producer,
		topic:    cfg.KafkaProducerTopics[0],
		ctx:      ctx,
	}, nil
}

// SendResponse - отправляет сообщения в кафку
func (rp *KafkaProducer) SendResponse(ctx context.Context, resp models.Response) error {
	data, err := json.Marshal(resp)
	if err != nil {
		return fmt.Errorf("ошибка маршалинга: %w", err)
	}

	msg := &sarama.ProducerMessage{
		Topic:     rp.topic,
		Key:       sarama.StringEncoder(resp.UserID),
		Value:     sarama.ByteEncoder(data),
		Timestamp: time.Now(),
		Headers: []sarama.RecordHeader{
			{Key: []byte("timestamp"), Value: []byte(time.Now().String())},
			{Key: []byte("success"), Value: []byte(fmt.Sprintf("%v", resp.Success))},
		},
	}

	done := make(chan error, 1)
	go func() {
		partition, offset, err := rp.producer.SendMessage(msg)
		if err != nil {
			done <- fmt.Errorf("ошибка отправки: %w", err)
			return
		}
		slog.Info("kafka producer send message", "partition", partition, "offset", offset,
			"place", tools.GetPlace())
		done <- nil
	}()

	select {
	case <-ctx.Done():
		return ctx.Err()
	case err = <-done:
		return err
	}
}

// Close закрывает продюсера
func (rp *KafkaProducer) Close() error {
	if rp.producer != nil {
		return rp.producer.Close()
	}
	return nil
}
