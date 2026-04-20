package main

import (
	"context"
	"example.com/bot_worker/internal/app"
	"example.com/bot_worker/pkg/config"
	"example.com/bot_worker/pkg/logger"
	"example.com/bot_worker/pkg/tools"
	"log"
)

func main() {
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

	if err = application.Start(); err != nil {
		logs.Error("Failed to start application", "error", err)
		return
	}
	logs.Info("server stopped successfully",
		"place", tools.GetPlace())
}
