package config

import (
	"fmt"
	"go.uber.org/multierr"
	"gopkg.in/yaml.v3"
	"os"
	"strings"
)

const configPath = "./pkg/config/config.yaml"

type Configuration struct {
	AiAPIKey string `yaml:"ai_api_key"`

	KafkaBrokers          []string `yaml:"kafka_brokers"`
	KafkaConsumerTopics   []string `yaml:"kafka_consumer_topics"`
	KafkaConsumerClientID string   `yaml:"kafka_consumer_client_id"`
	KafkaConsumerGroup    string   `yaml:"kafka_consumer_group_id"`

	KafkaProducerTopics   []string `yaml:"kafka_producer_topics"`
	KafkaProducerClientID string   `yaml:"kafka_producer_client_id"`

	LogKafkaTopics []string `yaml:"log_kafka_topics"`

	LogLevel string `yaml:"log_level"`

	PGUser     string `yaml:"pg_user"`
	PGPassword string `yaml:"pg_password"`
	PGHost     string `yaml:"pg_host"`
	PGPort     int    `yaml:"pg_port"`
	PGDatabase string `yaml:"pg_database"`
}

func NewConfig() (*Configuration, error) {
	var config Configuration

	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, err
	}

	err = yaml.Unmarshal(data, &config)
	if err != nil {
		return nil, err
	}

	return &config, nil
}

// Validate проверяет корректность конфигурации
func (c *Configuration) Validate() error {
	var errors error

	if c.AiAPIKey == "" {
		errors = multierr.Append(errors, fmt.Errorf("missing 'ai_api_key' field"))
	}

	if err := c.validateKafka(); err != nil {
		errors = multierr.Append(errors, err)
	}

	if err := c.validatePostgres(); err != nil {
		errors = multierr.Append(errors, err)
	}

	if err := c.validateLogLevel(); err != nil {
		errors = multierr.Append(errors, err)
	}

	return errors
}

func (c *Configuration) validateKafka() error {
	var errors error

	if len(c.KafkaBrokers) == 0 {
		errors = multierr.Append(errors, fmt.Errorf("missing 'kafka_brokers' field"))
	} else {
		for i, broker := range c.KafkaBrokers {
			if strings.TrimSpace(broker) == "" {
				errors = multierr.Append(errors, fmt.Errorf("missing 'kafka_brokers' field"))
			}

			if !strings.Contains(broker, ":") {
				errors = multierr.Append(errors, fmt.Errorf("missing 'kafka_brokers' field %d", i))
			}
		}
	}

	if len(c.KafkaConsumerTopics) == 0 {
		errors = multierr.Append(errors, fmt.Errorf("missing 'kafka_consumer_topics' field"))
	}
	if c.KafkaConsumerClientID == "" {
		errors = multierr.Append(errors, fmt.Errorf("missing 'kafka_consumer_client_id' field"))
	}
	if c.KafkaConsumerGroup == "" {
		errors = multierr.Append(errors, fmt.Errorf("missing 'kafka_consumer_group_id' field"))
	}

	if len(c.KafkaProducerTopics) == 0 {
		errors = multierr.Append(errors, fmt.Errorf("missing 'kafka_producer_topics' field"))
	}
	if c.KafkaProducerClientID == "" {
		errors = multierr.Append(errors, fmt.Errorf("missing 'kafka_producer_client_id' field"))
	}

	for i, topic := range c.LogKafkaTopics {
		if strings.TrimSpace(topic) == "" {
			errors = multierr.Append(errors, fmt.Errorf("missing 'log_kafka_topics' field %d", i))
		}
	}

	return errors
}

func (c *Configuration) validatePostgres() error {
	var errors error

	if c.PGUser == "" {
		errors = multierr.Append(errors, fmt.Errorf("missing 'pg_user' field"))
	}

	if c.PGPassword == "" {
		errors = multierr.Append(errors, fmt.Errorf("missing 'pg_password' field"))
	}
	if c.PGHost == "" {
		errors = multierr.Append(errors, fmt.Errorf("missing 'pg_host' field"))
	}
	if c.PGPort <= 0 || c.PGPort > 65535 {
		errors = multierr.Append(errors, fmt.Errorf("invalid value for 'pg_port' field"))
	}
	if c.PGDatabase == "" {
		errors = multierr.Append(errors, fmt.Errorf("missing 'pg_database' field"))
	}

	return errors
}

func (c *Configuration) validateLogLevel() error {
	validLevels := map[string]bool{
		"debug": true,
		"info":  true,
		"warn":  true,
		"error": true,
	}
	if c.LogLevel == "" {
		return fmt.Errorf("log_level is required")
	}

	if !validLevels[strings.ToLower(c.LogLevel)] {
		return fmt.Errorf("invalid log_level: %q (must be one of: debug, info, warn, error, fatal, panic, trace)",
			c.LogLevel)
	}

	return nil
}
