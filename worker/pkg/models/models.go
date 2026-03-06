package models

import "github.com/google/uuid"

type Request struct {
	TaskID  string `json:"task_id"`
	UserID  string `json:"user_id"`
	FileURL string `json:"file_url"`
	Prompt  string `json:"prompt"`
}

type Response struct {
	TaskID  string `json:"task_id"`
	UserID  string `json:"user_id"`
	Success bool   `json:"success"`
	Text    string `json:"text"`
}

type PgTask struct {
	TaskID uuid.UUID
	UserID string
}

type Log struct {
	Service  string `json:"service"`
	Level    string `json:"level"`
	Category string `json:"category"`
	Title    string `json:"title"`
	Message  string `json:"message"`
	Place    string `json:"place"`
}
