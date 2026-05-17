package processor

import (
	"example.com/bot_worker/pkg/models"
	"fmt"
	"strings"
)

func (p *Processor) WordProcess(metrics *models.ProcessingMetrics, file []byte, req *models.ProcessRequest) (
	*models.AIResponse, *models.ProcessingMetrics, error) {

	promptType := p.classifyPrompt(req.Prompt)
	switch promptType {
	case "summary":
		// "кратко о чем файл", "о чем текст"

	case "search":
		// "найди", "где упоминается"

	case "analytical":
		// "посчитай", "проанализируй", "сравни"

	default:
		// Эвристика "5 строк" для Word
	}
	return nil, nil, fmt.Errorf("unknown prompt type: %s", promptType)
}

func (p *Processor) classifyPrompt(prompt string) string {
	lower := strings.ToLower(prompt)

	// Суммаризация
	if strings.Contains(lower, "кратк") ||
		strings.Contains(lower, "о чем") ||
		strings.Contains(lower, "суть") ||
		strings.Contains(lower, "главн") {
		return "summary"
	}

	// Поиск
	if strings.Contains(lower, "найди") ||
		strings.Contains(lower, "где") ||
		strings.Contains(lower, "найти") ||
		strings.Contains(lower, "упомина") {
		return "search"
	}

	// Аналитика
	if strings.Contains(lower, "посчитай") ||
		strings.Contains(lower, "сравни") ||
		strings.Contains(lower, "анализ") ||
		strings.Contains(lower, "сколько") ||
		strings.Contains(lower, "цифр") {
		return "analytical"
	}

	return "default"
}
