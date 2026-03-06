package service_ai

import (
	"errors"
	"example.com/bot_worker/internal/api"
	"example.com/bot_worker/internal/parsing/excel_parsing"
	"fmt"
	"io"
	"net/http"
)

type ServiceMinioAI struct {
	api *api.AiActions
}

func NewServiceMinioAI(api *api.AiActions) *ServiceMinioAI {
	return &ServiceMinioAI{
		api: api,
	}
}

func (si *ServiceMinioAI) DownloadFile(url string) (io.Reader, error) {
	resp, err := http.Get(url)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != http.StatusOK {
		return nil, errors.New(resp.Status)
	}

	return resp.Body, nil
}

func (si *ServiceMinioAI) AIRequest(prompt string) (string, error) {
	return si.api.AIRequest(prompt)
}

func (si *ServiceMinioAI) Response(url string, prompt string) (string, error) {
	file, err := si.DownloadFile(url)
	if err != nil {
		return "", fmt.Errorf("download file from minio error: %v", err)
	}

	text, err := excel_parsing.ExcelToText(file)
	if err != nil {
		return "", fmt.Errorf("file parse error: %v", err)
	}
	//TODO: Сам промпт, может как-то поделать по другому
	TextPrompt := fmt.Sprintf("Что надо сделать:%s\nФайл:\n%s", prompt, text)

	resp, err := si.AIRequest(TextPrompt)
	if err != nil {
		return "", fmt.Errorf("AI request error: %v", err)
	}
	return resp, nil
}
