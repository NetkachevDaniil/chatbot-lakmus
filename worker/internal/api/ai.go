package api

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"example.com/bot_worker/pkg/config"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
)

type AiActions struct {
	aiApiKey     string
	systemPrompt string
	ctx          context.Context
}

const systemPromptFilePath = "./internal/api/system_prompt.txt"

func NewAI(ctx context.Context) (*AiActions, error) {
	var cfg = ctx.Value("config").(*config.Configuration)
	var aiApiKey = cfg.AiAPIKey

	if aiApiKey == "" {
		return nil, fmt.Errorf("AI_API_KEY environment variable not set")
	}
	file, err := os.Open(systemPromptFilePath)
	var systemPrompt strings.Builder
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = file.Close()
	}()
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		systemPrompt.WriteString(line)
		systemPrompt.WriteRune('\n')
	}

	return &AiActions{
		aiApiKey:     aiApiKey,
		systemPrompt: systemPrompt.String(),
		ctx:          ctx,
	}, nil
}

func (ai *AiActions) AIRequest(prompt string) (string, error) {
	return ai.aiRequest(prompt)
}

func (ai *AiActions) aiRequest(prompt string) (string, error) {
	ctx := context.Background()
	if ai.aiApiKey == "" {
		return "", fmt.Errorf("AI_API_KEY не установлен")
	}

	// Формируем messages с system prompt и вопросом пользователя
	messages := make([]map[string]string, 0)

	// Добавляем system prompt, если он не пустой
	if ai.systemPrompt != "" {
		messages = append(messages, map[string]string{
			"role":    "system",
			"content": ai.systemPrompt,
		})
	}

	// Добавляем вопрос пользователя
	messages = append(messages, map[string]string{
		"role":    "user",
		"content": prompt,
	})

	requestBody := map[string]interface{}{
		"model":    "openai/gpt-3.5-turbo",
		"messages": messages,
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return "", fmt.Errorf("ошибка маршалинга: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST",
		"https://openrouter.ai/api/v1/chat/completions",
		bytes.NewBuffer(jsonData))
	if err != nil {
		return "", fmt.Errorf("ошибка создания запроса: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+ai.aiApiKey)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("ошибка выполнения запроса: %w", err)
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("ошибка чтения ответа: %w", err)
	}

	// Проверяем статус ответа
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("API вернул ошибку %d: %s", resp.StatusCode, string(body))
	}

	var result struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
		Error *struct {
			Message string `json:"message"`
		} `json:"error,omitempty"`
	}

	err = json.Unmarshal(body, &result)
	if err != nil {
		return "", fmt.Errorf("ошибка парсинга ответа: %w", err)
	}

	// Проверяем наличие ошибки в ответе
	if result.Error != nil {
		return "", fmt.Errorf("API ошибка: %s", result.Error.Message)
	}

	if len(result.Choices) == 0 {
		return "", fmt.Errorf("нет ответа от модели")
	}

	return result.Choices[0].Message.Content, nil
}
