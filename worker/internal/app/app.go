package app

import (
	"context"
	"example.com/bot_worker/internal/api"
	kafk "example.com/bot_worker/internal/message_broker/kafka"
	"example.com/bot_worker/internal/migration"
	"example.com/bot_worker/internal/repository"
	"example.com/bot_worker/internal/service"
	"example.com/bot_worker/pkg/config"
	"example.com/bot_worker/pkg/models"
	"example.com/bot_worker/pkg/tools"
	"fmt"
	"go.uber.org/multierr"
	"log/slog"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"
)

type App struct {
	logger        *slog.Logger
	logs          chan *models.Log
	kafkaConsumer *kafk.KafkaConsumer
	kafkaProducer *kafk.KafkaProducer
	ctx           context.Context
	cancel        context.CancelFunc
	repo          repository.Repository
	services      int
}

func NewApp(ctx context.Context, cancel context.CancelFunc, logger *slog.Logger) (*App, error) {
	var services = 0
	var cfg = ctx.Value("config").(*config.Configuration)
	// ИИшка
	aiAPI, err := api.NewAI(ctx)
	if err != nil {
		cancel()
		return nil, err
	}
	// Сервис
	serv := service.NewService(aiAPI)

	// Postgres репозиторий
	repo, err := repository.NewRepository(ctx)
	if tools.ErrorIsNotNil(err) {
		cancel()
		return nil, fmt.Errorf("repository: %w", err)
	}
	services++
	logger.Info("repository connect success",
		"place", tools.GetPlace())

	// Миграции Postgres
	err = migration.CheckAndCreateTables(ctx)
	if err != nil {
		cancel()
		return nil, fmt.Errorf("migration: %w", err)
	}
	logger.Info("migrations success",
		"place", tools.GetPlace())

	// Продьюсер и консьюмер
	producer, err := kafk.NewKafkaProducer(ctx, cfg.KafkaBrokers)
	if err != nil {
		cancel()
		return nil, fmt.Errorf("kafka producer: %w", err)
	}

	logs := make(chan *models.Log, 2000)
	consumer, err := kafk.NewKafkaConsumer(ctx, cfg.KafkaBrokers, producer, serv,
		logger.With("kafka", "consumer"), logs)
	if err != nil {
		cancel()
		return nil, fmt.Errorf("kafka consumer: %w", err)
	}
	services++
	return &App{
		logger:        logger,
		kafkaConsumer: consumer,
		kafkaProducer: producer,
		ctx:           ctx,
		cancel:        cancel,
		logs:          logs,
		repo:          repo,
		services:      services,
	}, nil
}

func (app *App) Start() error {
	// Пушим логи в кафку
	logsToKafka := kafk.NewLogsToKafka(app.ctx, app.logs, app.kafkaProducer, app.logger.With("kafka", "save logs"))
	go logsToKafka.PushLogs()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)
	// Стартуем
	if err := app.kafkaConsumer.Start(); err != nil {
		return fmt.Errorf("kafka consumer: %w", err)
	}
	app.logger.Info("kafka consumer started",
		"place", tools.GetPlace())

	select {
	case <-app.ctx.Done():
		return app.ctx.Err()
	case sig := <-quit:
		app.logger.Info(fmt.Sprintf("received signal: %v", sig),
			"place", tools.GetPlace())
		ctx, cancel := context.WithTimeout(app.ctx, time.Second*30)
		defer cancel()
		resultChan := make(chan error, 1)
		go func() {
			resultChan <- app.Stop(ctx)
			close(resultChan)
		}()
		select {
		case err := <-resultChan:
			if err != nil {
				return fmt.Errorf("server stop: %w", err)
			}
			return nil
		case <-ctx.Done():
			return ctx.Err()
		}
	}
}

func (app *App) Stop(ctx context.Context) error {
	var resultChan = make(chan error, app.services)
	var wg = new(sync.WaitGroup)
	wg.Add(app.services)
	go func() {
		wg.Wait()
		close(resultChan)
	}()

	go func() {
		defer wg.Done()
		resultChan <- app.repo.Stop(ctx)
	}()

	go func() {
		defer wg.Done()
		resultChan <- app.kafkaConsumer.Stop()
	}()

	var result error
	for err := range resultChan {
		if err != nil {
			result = multierr.Append(result, err)
		}
	}

	return result
}
