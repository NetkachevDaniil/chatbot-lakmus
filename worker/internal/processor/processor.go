package processor

import (
	"example.com/bot_worker/internal/llm"
	"example.com/bot_worker/internal/parsing"
	"example.com/bot_worker/internal/service/analyzer"
	"example.com/bot_worker/pkg/models"
	"example.com/bot_worker/pkg/tools"
	"fmt"
	"os"
	"strings"
	"time"
)

type Processor struct {
	analyzerRegistry *analyzer.Registry
	llmIntent        *llm.IntentClient
	llmVisualizer    *llm.VisualizeClient
	llmWorkAround    *llm.WorkAroundClient
	maxRetries       int
}

func NewProcessor(
	llmIntent *llm.IntentClient,
	llmVisualizer *llm.VisualizeClient,
	llmWorkAround *llm.WorkAroundClient,
) *Processor {
	registry := analyzer.NewRegistry()
	return &Processor{
		analyzerRegistry: registry,
		llmIntent:        llmIntent,
		llmVisualizer:    llmVisualizer,
		maxRetries:       2,
		llmWorkAround:    llmWorkAround,
	}
}

// Process — главный метод обработки
func (p *Processor) Process(req *models.ProcessRequest) (*models.AIResponse, *models.ProcessingMetrics, error) {
	// Метрики
	metrics := &models.ProcessingMetrics{
		StartTime: time.Now(),
		LLMCalls:  0,
	}
	// Скачиваем файл
	file, err := p.downloadFile(req.FilePath)
	if err != nil {
		metrics.LLMCalls++
		metrics.EndTime = time.Now()
		metrics.DurationMs = metrics.EndTime.Sub(metrics.StartTime).Milliseconds()
		return &models.AIResponse{Explanation: "", Diagram: "", Insight: "", DiagramType: ""}, metrics, err
	}

	// Выбираем как парсим, что парсим и получаем результат
	switch req.FileFormat {
	case parsing.ExcelFormat:
		return p.ExcelProcess(metrics, file, req)
	}

	metrics.LLMCalls++
	metrics.EndTime = time.Now()
	metrics.DurationMs = metrics.EndTime.Sub(metrics.StartTime).Milliseconds()
	return nil, metrics, fmt.Errorf("unsupported file format: %s", req.FileFormat)
}

func (p *Processor) downloadFile(filePath string) ([]byte, error) {
	const HttpPrefix = "http://"
	const HttpsPrefix = "https://"

	if strings.HasPrefix(filePath, HttpPrefix) || strings.HasPrefix(filePath, HttpsPrefix) {
		// Скачиваем файл из MinIO
		data, err := tools.DownloadFile(filePath)
		if err != nil {
			return nil, fmt.Errorf("ошибка скачивания файла: %w", err)
		}
		return data, nil
	}
	// если локально
	file, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}
	return file, nil
}
