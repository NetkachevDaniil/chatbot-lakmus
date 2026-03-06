package main

import (
	"context"
	"example.com/bot_worker/internal/app"
	"example.com/bot_worker/pkg/config"
	"example.com/bot_worker/pkg/tools"
	"log"
	"log/slog"
	"os"
)

func main() {
	conf, err := config.NewConfig()
	if err != nil {
		log.Fatal(err)
	}
	if err = conf.Validate(); err != nil {
		log.Fatal(err)
	}

	ctxWithConf := context.WithValue(context.Background(), "config", conf)
	ctx, cancel := context.WithCancel(ctxWithConf)

	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: tools.SlogLevelByString(conf.LogLevel),
	}))

	application, err := app.NewApp(ctx, cancel, logger)
	if err != nil {
		logger.Error("Failed to create application", "error", err)
		return
	}

	/*
		go func() {
			time.Sleep(3 * time.Second)
			kafk.TestClient(ctx)
		}()
	*/
	if err = application.Start(); err != nil {
		logger.Error("Failed to start application", "error", err)
		return
	}
	logger.Info("server stopped successfully",
		"place", tools.GetPlace())
}
