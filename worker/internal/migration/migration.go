package migration

import (
	"context"
	"example.com/bot_worker/internal/repository/database"
	"go.uber.org/multierr"
)

// CheckAndCreateTables - создание таблиц если их нет
func CheckAndCreateTables(ctx context.Context) error {
	// Проверяем, существует ли таблица tasks
	db, err := database.InitPGPool(ctx)
	if err != nil {
		return err
	}
	defer db.Close()
	if err = db.Ping(); err != nil {
		return err
	}

	var tableExists bool
	var resultErr error
	if err1 := db.Pool.QueryRow(context.Background(), `
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'tasks'
        )
    `).Scan(&tableExists); err1 != nil {
		resultErr = multierr.Append(resultErr, err1)
	}

	if err2 := db.Pool.QueryRow(context.Background(), `
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'tasks_outbox'
        )
    `).Scan(&tableExists); err2 != nil {
		resultErr = multierr.Append(resultErr, err2)
	}

	if resultErr != nil {
		return resultErr
	}

	if !tableExists {
		_, err = db.Pool.Exec(context.Background(), `
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
			CREATE TABLE IF NOT EXISTS tasks (
    			task_id UUID PRIMARY KEY NOT NULL,
    			user_id VARCHAR(255) NOT NULL,
    			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
			);
			CREATE TABLE IF NOT EXISTS tasks_outbox (
    			task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    			user_id VARCHAR(255) NOT NULL,
				
    			file_link VARCHAR(512) NOT NULL,
    			prompt TEXT NOT NULL,
				
    			status VARCHAR(20) DEFAULT 'pending',
				
    			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    			);

			CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
			CREATE INDEX IF NOT EXISTS idx_tasks_outbox_status ON tasks_outbox(status);
			CREATE INDEX IF NOT EXISTS idx_tasks_outbox_user_id ON tasks_outbox(user_id);
        `)

		if err != nil {
			return err
		}

	}
	return nil
}
