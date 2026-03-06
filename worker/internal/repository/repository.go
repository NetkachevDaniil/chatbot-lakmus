package repository

import (
	"context"
	"example.com/bot_worker/internal/repository/database"
	"example.com/bot_worker/pkg/models"
)

type Repository interface {
	SaveTask(response models.PgTask) error
	Stop(context.Context) error
}

func NewRepository(ctx context.Context) (*database.Postgres, error) {
	return database.InitPostgres(ctx)
}
