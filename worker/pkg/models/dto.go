package models

type Request struct {
	UserID     string `json:"user_id"`
	ChatID     string `json:"chat_id"`
	FileFormat string `json:"file_format"`
	FileURL    string `json:"file_url"`
	Prompt     string `json:"prompt"`
	Attempt    int    `json:"attempt"`
}

type Response struct {
	Request     Request            `json:"request"`
	Metrics     *ProcessingMetrics `json:"metrics"`
	UserID      string             `json:"user_id"`
	ChatID      string             `json:"chat_id"`
	Success     bool               `json:"success"`
	Explanation string             `json:"explanation"`
	Diagram     string             `json:"diagram"`
	Attempt     int                `json:"attempt"`
	Error       string             `json:"error"`
}
