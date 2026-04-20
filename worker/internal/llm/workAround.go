package llm

import (
	"example.com/bot_worker/internal/parsing"
	"example.com/bot_worker/internal/parsing/excel"
	"example.com/bot_worker/pkg/models"
	"fmt"
)

type WorkAroundClient struct {
	client *Client
}

func NewWorkAroundClient(client *Client) *WorkAroundClient {
	return &WorkAroundClient{client: client}
}

func (a *WorkAroundClient) WorkAround(prompt, fileFormat string, file []byte) (*models.AIResponse, error) {
	switch fileFormat {
	case parsing.ExcelFormat, parsing.ExcelFormat2, parsing.ExcelFormat3:
		meta, err := excel.ReadDataFromBytes(file, fmt.Sprintf("file.%s", fileFormat), 0)
		if err != nil {
			return nil, err
		}

		systemPrompt := "Ты помощник-анализатор, помогаешь пользователю анализировать предоставляемый им файл." +
			"Отвечай четко и лаконично, ты оперируешь цифрами и статистикой."

		messages := []map[string]string{
			{"role": "system", "content": systemPrompt},
			{"role": "user", "content": a.buildIntentPrompt(meta, prompt)},
		}
		response, err := a.client.Chat(messages)
		if err != nil {
			return nil, err
		}
		return &models.AIResponse{
			Explanation: response,
			Diagram:     "",
			Insight:     "",
			DiagramType: "",
		}, nil

	}
	return nil, fmt.Errorf("format not supported")
}

func (a *WorkAroundClient) buildIntentPrompt(meta *models.ExcelMetadata, prompt string) string {
	sheetsInfo := ""
	for _, sheet := range meta.Sheets {
		sheetsInfo += fmt.Sprintf("\n- Лист '%s': %d строк, колонки: %v\n", sheet.Name, sheet.RowCount, sheet.Columns)

		if len(sheet.SampleRows) > 0 {
			sheetsInfo += "Данные:\n"
			for _, row := range sheet.SampleRows {
				sheetsInfo += fmt.Sprintf("    %+v\n", row)
			}
		}
	}

	return fmt.Sprintf(`Доступные листы в файле:%s
		Вопрос пользователя: %s.`, sheetsInfo, prompt)
}
