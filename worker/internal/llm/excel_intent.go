package llm

import (
	"encoding/json"
	"example.com/bot_worker/pkg/models"
	"fmt"
)

type IntentClient struct {
	client *Client
}

func NewIntentClient(client *Client) *IntentClient {
	return &IntentClient{client: client}
}

func (ic *IntentClient) GetIntent(meta *models.ExcelMetadata, prompt string) (*models.AnalysisIntent, error) {
	systemPrompt := `Ты — классификатор запросов к образовательным данным. Верни ТОЛЬКО JSON.

	Доступные анализаторы и их обязательные параметры:

	1. filter - фильтрация данных
   	Обязательные params: {"column": "название колонки", "operator": "eq|gt|lt|gte|lte|contains", "value": "значение"}

	2. group_comparison - сравнение групп
   	Обязательные params: {"group_column": "название колонки для группировки", "value_column": "название колонки со значениями"}

	3. top_bottom - лучшие/худшие
   	Обязательные params: {"name_column": "название колонки с именами", "value_column": "название колонки со значениями", "mode": "top|bottom"}

	4. correlation - корреляция между колонками
   	Обязательные params: {"column_x": "первая колонка", "column_y": "вторая колонка"}

	5. trend - анализ трендов
   	Обязательные params: {"date_column": "название колонки с датами/номерами", "value_column": "название колонки со значениями"}

	6. distribution - распределение значений
   	Обязательные params: {"value_column": "название колонки со значениями"}

	ПРАВИЛА:
	- НЕ копируй названия колонок из примеров.
	- НЕ сокращай и НЕ изменяй названия колонок.
	- Используй ТОЛЬКО те названия колонок, которые прямо указаны в запросе пользователя.
	- Сохраняй оригинальные названия колонок с пробелами, дефисами и цифрами.

	Ответь ТОЛЬКО JSON, без пояснений`

	userPrompt := ic.buildIntentPrompt(meta, prompt)

	messages := []map[string]string{
		{"role": "system", "content": systemPrompt},
		{"role": "user", "content": userPrompt},
	}

	response, err := ic.client.Chat(messages)
	if err != nil {
		return nil, err
	}

	// Парсим JSON
	var intent models.AnalysisIntent
	if err = json.Unmarshal([]byte(response), &intent); err != nil {
		fixResponse := cleanMarkdownJSON(fixJSON(response))
		if err = json.Unmarshal([]byte(fixResponse), &intent); err != nil {
			return nil, fmt.Errorf("ошибка парсинга ответа LLM: %w, ответ: %s", err, fixResponse)
		}

	}

	return &intent, nil
}

func (ic *IntentClient) buildIntentPrompt(meta *models.ExcelMetadata, prompt string) string {
	sheetsInfo := ""
	for _, sheet := range meta.Sheets {
		sheetsInfo += fmt.Sprintf("\n- Лист '%s': %d строк, колонки: %v\n", sheet.Name, sheet.RowCount, sheet.Columns)

		if len(sheet.SampleRows) > 0 {
			sheetsInfo += "  Примеры данных:\n"
			for i, row := range sheet.SampleRows {
				if i >= 2 {
					break
				}
				sheetsInfo += fmt.Sprintf("    %+v\n", row)
			}
		}
	}

	return fmt.Sprintf(`Доступные листы в файле:%s
		Вопрос пользователя: %s	
		Выбери анализатор из: group_comparison, top_bottom, correlation, trend, distribution, filter.
		Верни JSON: {"analyzer": "...", "sheet_name": "...", "params": {...}}`, sheetsInfo, prompt)
}
