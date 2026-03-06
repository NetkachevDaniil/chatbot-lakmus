package tools

import (
	"example.com/bot_worker/pkg/models"
	"log/slog"
	"os"
	"runtime"
	"strconv"
	"strings"
	"time"
)

const ServiceName = "worker"

func GetEnv(key string, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}

func GetEnvAsBool(key string, defaultValue bool) bool {
	if valueStr := GetEnv(key, ""); valueStr != "" {
		if value, err := strconv.ParseBool(valueStr); err == nil {
			return value
		}
	}
	return defaultValue
}

func GetEnvAsInt(key string, defaultValue int) int {
	if valueStr := GetEnv(key, ""); valueStr != "" {
		if value, err := strconv.Atoi(valueStr); err == nil {
			return value
		}
	}
	return defaultValue
}

// GetPlace - функция для получения места вызова какой-то другой функции
func GetPlace() string {
	_, file, line, _ := runtime.Caller(1)
	split := strings.Split(file, "/")
	StartFile := split[len(split)-1]
	place := StartFile + ":" + strconv.Itoa(line)
	return place
}

var TimeFormat = time.Now().Format("02.01.2006 15:04:05")

func CreateLogStruct(service, level, category, title, message, place string) *models.Log {
	return &models.Log{
		Service:  service,
		Level:    level,
		Category: category,
		Title:    title,
		Message:  message,
		Place:    place,
	}
}

func ErrorIsNotNil(err error) bool {
	return err != nil
}

func SlogLevelByString(level string) slog.Level {
	switch level {
	case "debug":
		return slog.LevelDebug
	case "info":
		return slog.LevelInfo
	case "warn":
		return slog.LevelWarn
	case "error":
		return slog.LevelError
	default:
		return slog.LevelDebug
	}
}
