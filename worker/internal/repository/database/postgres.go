package database

import (
	"context"
	"example.com/bot_worker/pkg/config"
	"example.com/bot_worker/pkg/models"
	"fmt"
	"github.com/jackc/pgx/v5/pgxpool"
)

type Postgres struct {
	Pool *pgxpool.Pool
	ctx  context.Context
}

func InitPostgres(ctx context.Context) (*Postgres, error) {
	pg, err := InitPGPool(ctx)
	if err != nil {
		return nil, err
	}

	if err = pg.Ping(); err != nil {
		return nil, err
	}

	return pg, nil
}

func InitPGPool(ctx context.Context) (*Postgres, error) {
	var cfg = ctx.Value("config").(*config.Configuration)
	connStr := fmt.Sprintf("postgresql://%s:%s@%s:%d/%s", cfg.PGUser, cfg.PGPassword,
		cfg.PGHost, cfg.PGPort, cfg.PGDatabase)

	pool, errPGX := pgxpool.New(ctx, connStr)
	if errPGX != nil {
		return nil, errPGX
	}

	return &Postgres{
		Pool: pool,
		ctx:  ctx,
	}, nil
}

func (pg *Postgres) Close() {
	pg.Pool.Close()
}

func (pg *Postgres) Ping() error {
	return pg.Pool.Ping(pg.ctx)
}

func (pg *Postgres) SaveTask(response models.PgTask) error {
	select {
	case <-pg.ctx.Done():
		return pg.ctx.Err()
	default:
		err := pg.saveTask(response)
		if err != nil {
			return err
		}
	}
	return nil
}

func (pg *Postgres) saveTask(r models.PgTask) error {
	ctx, cancel := context.WithCancel(pg.ctx)
	defer cancel()

	query := `
    INSERT INTO tasks
    (task_id, user_id)
    VALUES ($1, $2, $3) ON CONFLICT DO NOTHING;`

	_, err := pg.Pool.Query(ctx, query, r.TaskID, r.UserID)
	if err != nil {
		return err
	}
	return nil
}

func (pg *Postgres) Stop(ctx context.Context) error {
	exitChan := make(chan struct{}, 1)
	go func() {
		pg.Pool.Close()
		exitChan <- struct{}{}
		close(exitChan)
	}()

	select {
	case <-exitChan:
		return nil
	case <-ctx.Done():
		return ctx.Err()
	case <-pg.ctx.Done():
		return pg.ctx.Err()
	}
}
