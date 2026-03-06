package kafk

import (
	"context"
	"example.com/bot_worker/pkg/config"
	"example.com/bot_worker/pkg/constants"
	"example.com/bot_worker/pkg/models"
	"example.com/bot_worker/pkg/tools"
	"log/slog"
)

type LogsToKafka struct {
	logs     chan *models.Log
	topic    string
	producer *KafkaProducer
	ctx      context.Context
	logger   *slog.Logger
}

func NewLogsToKafka(ctx context.Context, logs chan *models.Log, producer *KafkaProducer, logger *slog.Logger) *LogsToKafka {
	var cfg = ctx.Value("config").(*config.Configuration)

	return &LogsToKafka{
		logs:     logs,
		topic:    cfg.LogKafkaTopics[0],
		producer: producer,
		ctx:      ctx,
		logger:   logger,
	}
}

func (logs *LogsToKafka) PushLogs() {
	for {
		select {
		case <-logs.ctx.Done():
			return
		case log := <-logs.logs:
			ctx, cancel := context.WithTimeout(context.Background(), constants.DefaultTimeout)
			err := logs.producer.SendLogToKafka(ctx, logs.topic, log)
			if err != nil {
				logs.logger.Error(tools.ServiceName, "category", "kafka logs", "title", "send response", "message",
					err, "place", tools.GetPlace())
				cancel()
				continue
			}
			cancel()
		}
	}
}
