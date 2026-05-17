package llm

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type Config struct {
	Endpoint string
	APIKey   string
	Model    string
	Timeout  time.Duration
}

type Client struct {
	httpClient *http.Client
	config     *Config
}

func NewClient(config *Config) *Client {
	return &Client{
		httpClient: &http.Client{Timeout: config.Timeout},
		config:     config,
	}
}

func (c *Client) Chat(messages []map[string]string) (string, error) {
	body := map[string]interface{}{
		"model":       c.config.Model,
		"messages":    messages,
		"temperature": 0.2,
	}

	jsonBody, _ := json.Marshal(body)

	req, _ := http.NewRequest("POST", c.config.Endpoint, bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	if c.config.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.config.APIKey)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	var result map[string]interface{}
	if err = json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}

	if errorField, ok := result["error"].(map[string]interface{}); ok {
		errorJSON, _ := json.Marshal(errorField)
		return "", fmt.Errorf("API error: %s", string(errorJSON))
	}

	// TODO: распарсить ошибку еще надо (если будет), тут этого нет
	choices, ok := result["choices"].([]interface{})
	if !ok || len(choices) == 0 {
		return "", fmt.Errorf("неожиданный формат ответа")
	}

	message := choices[0].(map[string]interface{})["message"].(map[string]interface{})
	content := message["content"].(string)
	return content, nil
}

type OpenRouterResponse struct {
	Error *struct {
		Message string `json:"message"`
		Type    string `json:"type"`
		Param   string `json:"param"`
		Code    string `json:"code"`
	} `json:"error"`
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
}
