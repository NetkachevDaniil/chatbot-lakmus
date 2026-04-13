package tools

import (
	"fmt"
	"io"
	"log/slog"
	"net/http"
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

// GetPlace - функция для получения места вызова какой-то другой функции
func GetPlace() string {
	_, file, line, _ := runtime.Caller(1)
	split := strings.Split(file, "/")
	StartFile := split[len(split)-1]
	place := StartFile + ":" + strconv.Itoa(line)
	return place
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

func DownloadFile(url string) ([]byte, error) {
	client := &http.Client{
		Timeout: 30 * time.Second,
	}

	resp, err := client.Get(url)
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP ошибка: %d", resp.StatusCode)
	}

	limitReader := io.LimitReader(resp.Body, 50*1024*1024)

	data, err := io.ReadAll(limitReader)
	if err != nil {
		return nil, err
	}

	if len(data) == 0 {
		return nil, fmt.Errorf("скачанный файл пуст")
	}

	return data, nil
}
