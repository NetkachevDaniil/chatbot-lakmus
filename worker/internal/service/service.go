package service

import (
	"example.com/bot_worker/internal/api"
	"example.com/bot_worker/internal/service/service_ai"
	"io"
)

type ServiceInterface interface {
	DownloadFile(string) (io.Reader, error)
	AIRequest(string) (string, error)
	Response(string, string) (string, error) // url string, prompt string
}

func NewService(api *api.AiActions) ServiceInterface {
	return service_ai.NewServiceMinioAI(api)
}
