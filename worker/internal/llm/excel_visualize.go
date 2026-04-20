package llm

import (
	"encoding/json"
	"example.com/bot_worker/pkg/models"
	"fmt"
	"regexp"
	"strings"
)

type VisualizeClient struct {
	client *Client
}

func NewVisualizeClient(client *Client) *VisualizeClient {
	return &VisualizeClient{client: client}
}

func (vc *VisualizeClient) Visualize(prompt string, data map[string]interface{}) (*models.AIResponse, error) {
	systemPrompt := `Ты — визуальный аналитик. На основе данных создай Mermaid-диаграмму.
	Верни ТОЛЬКО JSON в формате:
	{
  		"explanation": "объяснение (3,4 предложения, должна быть конкретика)",
  		"diagram": "mermaid код",
  		"insight": "ключевое наблюдение",
  		"diagram_type": "comparison"
	}

	Правила для Mermaid:
	- Используй graph TD или graph LR
	- Не добавляй стилизацию, только чистый код
	- diagram_type может быть ТОЛЬКО одно из: comparison, risk, flow, timeline

	Цвета не нужны, они будут добавлены отдельно.

	Данные для визуализации: {{.Data}}
	Важно: Верни JSON в ОДНУ СТРОКУ. Не используй переносы строк внутри значений.
	Пример: {"explanation": "текст", "diagram": "graph TD\n A-->B", "insight": "текст", "diagram_type": "comparison"}`

	userPrompt := fmt.Sprintf(`Вопрос: %s
		Результат анализа: %v`, prompt, data)

	messages := []map[string]string{
		{"role": "system", "content": systemPrompt},
		{"role": "user", "content": userPrompt},
	}

	response, err := vc.client.Chat(messages)
	if err != nil {
		return nil, err
	}

	var aiResponse models.AIResponse
	if err = json.Unmarshal([]byte(response), &aiResponse); err != nil {
		fixResponse := cleanMarkdownJSON(fixJSON(response))
		if err = json.Unmarshal([]byte(fixResponse), &aiResponse); err != nil {
			// ошибка парсинга обычно из-за диаграммы, у нейронки плохо с этим иногда, тут мы извлекаем просто текст.
			return extractTextResponse(fixResponse), nil
		}
	}

	return &aiResponse, nil
}

func fixJSON(raw string) string {
	raw = strings.TrimSpace(raw)

	if !strings.HasSuffix(raw, "}") {
		raw = raw + "}"
	}

	return raw
}

func cleanMarkdownJSON(raw string) string {
	re := regexp.MustCompile("(?s)```(?:json)?\\s*(.*?)\\s*```")
	if matches := re.FindStringSubmatch(raw); len(matches) > 1 {
		return matches[1]
	}

	start := strings.Index(raw, "{")
	end := strings.LastIndex(raw, "}")
	if start != -1 && end != -1 {
		return raw[start : end+1]
	}

	return raw
}

func extractTextResponse(rawResponse string) *models.AIResponse {

	explanation := extractField(rawResponse, "explanation")
	insight := extractField(rawResponse, "insight")

	if explanation != "" {
		return &models.AIResponse{
			Explanation: explanation,
			Insight:     insight,
			Diagram:     "",
			DiagramType: "text",
		}
	}

	return &models.AIResponse{
		Explanation: rawResponse,
		Insight:     "Ответ от модели",
		Diagram:     "",
		DiagramType: "text",
	}
}

func extractField(text, fieldName string) string {
	pattern := fmt.Sprintf(`"%s":\s*"([^"]*)"`, fieldName)
	re := regexp.MustCompile(pattern)
	matches := re.FindStringSubmatch(text)
	if len(matches) > 1 {
		return matches[1]
	}
	return ""
}
