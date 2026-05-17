package main

import (
	"context"
	"encoding/json"
	"example.com/bot_worker/internal/app"
	"example.com/bot_worker/internal/llm"
	kafk "example.com/bot_worker/internal/message_broker/kafka"
	"example.com/bot_worker/internal/processor"
	"example.com/bot_worker/pkg/config"
	"example.com/bot_worker/pkg/logger"
	"example.com/bot_worker/pkg/models"
	"example.com/bot_worker/pkg/tools"
	"log"
	"time"
)

func main() {
	//TestLocalProcess()
	TestProcessWithKafka()
}

func TestProcessWithKafka() {
	ctx := context.Background()

	conf, err := config.NewConfig()
	if err != nil {
		log.Fatal(err)
	}
	if err = conf.Validate(); err != nil {
		log.Fatal(err)
	}

	logFile, logs := logger.NewSlogLogger(conf.LogLevel)
	defer func() {
		_ = logFile.Close()
	}()

	ctx = context.WithValue(ctx, "config", conf)
	ctx = context.WithValue(ctx, "logger", logs)

	application, err := app.NewApp(ctx)
	if err != nil {
		logs.Error("Failed to create application", "error", err)
		return
	}

	go func() {
		time.Sleep(3 * time.Second)
		kafk.TestClient(ctx)
	}()

	if err = application.Start(); err != nil {
		logs.Error("Failed to start application", "error", err)
		return
	}
	logs.Info("server stopped successfully",
		"place", tools.GetPlace())
}

func TestLocalProcess() {
	llmConfig := &llm.Config{
		Endpoint: tools.GetEnv("LLM_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions"),
		APIKey:   tools.GetEnv("API_KEY_OPEN_ROUTER", "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"),
		Model:    tools.GetEnv("LLM_MODEL", "openai/gpt-3.5-turbo"),
		Timeout:  5 * time.Minute,
	}
	llmClient := llm.NewClient(llmConfig)
	intentClient := llm.NewIntentClient(llmClient)
	visualizeClient := llm.NewVisualizeClient(llmClient)
	workAround := llm.NewWorkAroundClient(llmClient)

	proc := processor.NewProcessor(intentClient, visualizeClient, workAround)

	req := &models.ProcessRequest{
		FilePath:   "./nabeba.xlsx",
		Prompt:     "кто как учится?",
		FileFormat: "xlsx",
	}

	response, metrics, err := proc.Process(req)
	if err != nil {
		log.Fatalf("Ошибка: %v", err)
	}

	resultJSON, _ := json.MarshalIndent(response, "", "  ")
	log.Printf("Результат:\n%s", resultJSON)

	metricsJSON, _ := json.MarshalIndent(metrics, "", "  ")
	log.Printf("Метрики:\n%s", metricsJSON)
}
