package app

import (
	"context"
	"example.com/bot_worker/internal/llm"
	kafk "example.com/bot_worker/internal/message_broker/kafka"
	"example.com/bot_worker/internal/processor"
	"example.com/bot_worker/pkg/config"
	"example.com/bot_worker/pkg/tools"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"
)

type App struct {
	logger        *slog.Logger
	kafkaConsumer *kafk.KafkaConsumer
	kafkaProducer *kafk.KafkaProducer
	ctx           context.Context
	services      int
}

func NewApp(ctx context.Context) (*App, error) {
	var services = 0
	var cfg = ctx.Value("config").(*config.Configuration)
	var logger = ctx.Value("logger").(*slog.Logger)

	// ИИ
	llmConfig := &llm.Config{
		Endpoint: cfg.AIEndpoint,
		APIKey:   cfg.AIApiKey,
		Model:    cfg.AIModel,
		Timeout:  time.Duration(cfg.AIResponseTimeoutSec) * time.Second,
	}
	llmClient := llm.NewClient(llmConfig)
	intentClient := llm.NewIntentClient(llmClient)
	visualizeClient := llm.NewVisualizeClient(llmClient)
	workAround := llm.NewWorkAroundClient(llmClient)
	// Исполняет запросы
	proc := processor.NewProcessor(intentClient, visualizeClient, workAround)

	// Продьюсер и консьюмер
	producer, err := kafk.NewKafkaProducer(ctx, cfg.KafkaBrokers)
	if err != nil {
		return nil, fmt.Errorf("kafka producer: %w", err)
	}

	consumer, err := kafk.NewKafkaConsumer(ctx, cfg.KafkaBrokers, producer, proc,
		logger.With("kafka", "consumer"))
	if err != nil {
		return nil, fmt.Errorf("kafka consumer: %w", err)
	}
	services++
	return &App{
		logger:        logger,
		kafkaConsumer: consumer,
		kafkaProducer: producer,
		ctx:           ctx,
		services:      services,
	}, nil
}

func (app *App) Start() error {
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)

	if err := app.kafkaConsumer.Start(); err != nil {
		return fmt.Errorf("kafka consumer: %w", err)
	}
	app.logger.Info("kafka consumer started",
		"place", tools.GetPlace())

	sig := <-quit

	app.logger.Info(fmt.Sprintf("received signal: %v", sig),
		"place", tools.GetPlace())

	ctx, cancel := context.WithTimeout(app.ctx, time.Second*30)
	defer cancel()

	if err := app.Stop(ctx); err != nil {
		return fmt.Errorf("kafka consumer stop error: %w", err)
	}

	app.logger.Info("kafka consumer stopped")
	return nil
}

func (app *App) Stop(ctx context.Context) error {
	var resultChan = make(chan error, 1)

	go func() {
		resultChan <- app.kafkaConsumer.Stop()
		close(resultChan)
	}()

	select {
	case <-ctx.Done():
		return ctx.Err()
	case err := <-resultChan:
		return err
	}
}
