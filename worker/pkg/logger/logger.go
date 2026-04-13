package logger

import (
	"example.com/bot_worker/pkg/tools"
	"io"
	"log/slog"
	"os"
)

const logFile = "./app.log"

const filePermission os.FileMode = 0666

func NewSlogLogger(logLevel string) (*os.File, *slog.Logger) {
	file, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, filePermission)
	if err != nil {
		panic(err)
	}

	multiWriter := io.MultiWriter(file, os.Stdout)

	logger := slog.New(slog.NewJSONHandler(multiWriter, &slog.HandlerOptions{
		Level: tools.SlogLevelByString(logLevel),
	}))
	return file, logger
}
