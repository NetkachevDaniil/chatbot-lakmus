package processor

import (
	"example.com/bot_worker/internal/parsing/excel"
	"example.com/bot_worker/pkg/models"
	"fmt"
	"go.uber.org/multierr"
	"time"
)

func (p *Processor) ExcelProcess(metrics *models.ProcessingMetrics, file []byte, req *models.ProcessRequest) (
	*models.AIResponse, *models.ProcessingMetrics, error) {

	// Чтение метаданных Excel (шапка, тестовые строки)
	maxSamples := 3 // сколько столбцов взять для примера (пример который для ии)
	meta, err := excel.ReadDataFromBytes(file, req.FilePath, maxSamples)
	if err != nil {
		return nil, nil, fmt.Errorf("ошибка чтения Excel: %w", err)
	}

	//Получение намерения от LLM (какой анализатор взять)
	intent, err := p.getIntentWithRetry(meta, req.Prompt)
	if err != nil {
		// опять идем к ии, но уже влоб, просто кидаем файл и промпт, без нашей обработки
		resp, err := p.llmWorkAround.WorkAround(req.Prompt, req.FileFormat, file)
		if err != nil {
			metrics.LLMCalls++
			metrics.EndTime = time.Now()
			metrics.DurationMs = metrics.EndTime.Sub(metrics.StartTime).Milliseconds()
			return &models.AIResponse{Explanation: "", Diagram: "", Insight: "", DiagramType: ""}, metrics, err
		}
		return resp, metrics, nil
	}
	metrics.LLMCalls++

	// Валидация и нормализация листа (проверка наличия столбца у листа по которому анализируем)
	intent = p.normalizeSheet(intent, meta)

	// Выполнение анализа (выполнение анализатора)
	analysisResult, err := p.executeAnalysis(file, intent)
	if err != nil {
		metrics.EndTime = time.Now()
		metrics.DurationMs = metrics.EndTime.Sub(metrics.StartTime).Milliseconds()
		resp, _ := p.llmWorkAround.WorkAround(req.Prompt, req.FileFormat, file)
		return resp, metrics, nil
	}
	metrics.AnalyzerUsed = analysisResult.Analyzer
	metrics.SheetUsed = analysisResult.Sheet

	// Визуализация результата
	response, err := p.llmVisualizer.Visualize(req.Prompt, analysisResult.Data)
	if err != nil {
		metrics.EndTime = time.Now()
		metrics.DurationMs = metrics.EndTime.Sub(metrics.StartTime).Milliseconds()

		return nil, metrics, err
	}
	metrics.LLMCalls++
	metrics.EndTime = time.Now()
	metrics.DurationMs = metrics.EndTime.Sub(metrics.StartTime).Milliseconds()

	return response, metrics, nil
}

// getIntentWithRetry — получение намерения с повторными попытками
func (p *Processor) getIntentWithRetry(meta *models.ExcelMetadata, prompt string) (*models.AnalysisIntent, error) {
	var lastErr error
	for attempt := 0; attempt < p.maxRetries; attempt++ {
		intent, err := p.llmIntent.GetIntent(meta, prompt)
		if err == nil {
			return intent, nil
		}
		lastErr = err
		time.Sleep(time.Second)
	}
	return nil, lastErr
}

// normalizeSheet — проверяет существование листа, если нет — берёт первый
func (p *Processor) normalizeSheet(intent *models.AnalysisIntent, meta *models.ExcelMetadata) *models.AnalysisIntent {
	for _, sheet := range meta.Sheets {
		if sheet.Name == intent.SheetName {
			return intent
		}
	}

	if len(meta.Sheets) > 0 {
		intent.SheetName = meta.Sheets[0].Name
	}
	return intent
}

// executeAnalysis — выполняет анализ
func (p *Processor) executeAnalysis(fileData []byte, intent *models.AnalysisIntent) (*models.AnalysisResult, error) {
	currentIntent := intent
	var errs error

	for attempt := 0; attempt < 3; attempt++ {
		// Получаем анализатор
		a, exists := p.analyzerRegistry.Get(currentIntent.Analyzer)
		if !exists {
			errs = multierr.Append(errs, fmt.Errorf("analyzer %s not found", currentIntent.Analyzer))
			continue
		}

		// Открываем файл
		f, rows, err := excel.GetSheetDataFromBytes(fileData, currentIntent.SheetName)
		if err != nil {
			errs = multierr.Append(errs, err)
			_ = f.Close()
			continue
		}

		// Выполняем анализ
		rawResult, err := a.Analyze(f, currentIntent.SheetName, currentIntent.Params)
		if err != nil {
			errs = multierr.Append(errs, err)
			_ = f.Close()
			continue
		}

		_ = rows
		_ = f.Close()
		return &models.AnalysisResult{
			Type:      rawResult["type"].(string),
			Sheet:     currentIntent.SheetName,
			Data:      rawResult,
			Analyzer:  currentIntent.Analyzer,
			Timestamp: time.Now().Unix(),
		}, nil
	}

	return nil, fmt.Errorf("анализ не удался после всех fallback'ов: %v", errs)
}
