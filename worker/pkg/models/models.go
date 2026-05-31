package models

import "time"

// ProcessRequest - входные данные
type ProcessRequest struct {
	FilePath   string `json:"file_path"`
	Prompt     string `json:"prompt"`
	FileFormat string `json:"file_format"`
}

// SheetInfo - метадата файла: страницы, название файла, первые 5 колонок/столбцов файла
type SheetInfo struct {
	Name       string                   `json:"name"`
	RowCount   int                      `json:"row_count"`
	Columns    []string                 `json:"columns"`
	SampleRows []map[string]interface{} `json:"sample_rows"`
}

type ExcelMetadata struct {
	Sheets      []SheetInfo `json:"sheets"`
	ActiveSheet string      `json:"active_sheet"`
	FileName    string      `json:"file_name"`
}

// AnalysisIntent - намерение от LLM, какой анализатор взять
type AnalysisIntent struct {
	Analyzer  string                 `json:"analyzer"`
	SheetName string                 `json:"sheet_name"`
	Params    map[string]interface{} `json:"params"`
}

// AnalysisResult - результат анализа оть анализаторов
type AnalysisResult struct {
	Type      string                 `json:"type"`
	Sheet     string                 `json:"sheet"`
	Data      map[string]interface{} `json:"data"`
	Analyzer  string                 `json:"analyzer"`
	Timestamp int64                  `json:"timestamp"`
}

// AIResponse - финальный ответ от ии
type AIResponse struct {
	Explanation string `json:"explanation"`
	Diagram     string `json:"diagram"`
	Insight     string `json:"insight"`
	DiagramType string `json:"diagram_type"`
}

// ProcessingMetrics - Метрики
type ProcessingMetrics struct {
	StartTime    time.Time `json:"start_time"`
	EndTime      time.Time `json:"end_time"`
	DurationMs   int64     `json:"duration_ms"`
	LLMCalls     int       `json:"llm_calls"`
	AnalyzerUsed string    `json:"analyzer_used"`
	SheetUsed    string    `json:"sheet_used"`
}
