package config

import (
	"example.com/bot_worker/pkg/tools"
	"fmt"
	"go.uber.org/multierr"
	"gopkg.in/yaml.v3"
	"log"
	"os"
	"strings"
)

const DefaultConfigPath = "./config.yaml"

type Configuration struct {
	AIApiKey             string `yaml:"ai_api_key"`
	AIEndpoint           string `yaml:"ai_endpoint"`
	AIModel              string `yaml:"ai_model"`
	AIResponseTimeoutSec int    `yaml:"ai_response_timeout_sec"`

	KafkaBrokers          []string `yaml:"kafka_brokers"`
	KafkaConsumerTopics   []string `yaml:"kafka_consumer_topics"`
	KafkaConsumerClientID string   `yaml:"kafka_consumer_client_id"`
	KafkaConsumerGroup    string   `yaml:"kafka_consumer_group_id"`

	KafkaProducerTopics   []string `yaml:"kafka_producer_topics"`
	KafkaProducerClientID string   `yaml:"kafka_producer_client_id"`

	LogLevel string `yaml:"log_level"`
}

func NewConfig() (*Configuration, error) {
	var config Configuration

	configPath := tools.GetEnv("WORKER_CONFIG_PATH", DefaultConfigPath)
	if configPath == DefaultConfigPath {
		log.Println("CONFIG_PATH not found in environment variables")
		log.Println("CONFIG_PATH set to default value: ./config.yaml")
	}

	data, err := os.ReadFile(configPath)
	if err != nil {
		log.Println("error reading config file: ", err)
		log.Println("returning default configuration")
		return setDefaults(), nil
	}

	err = yaml.Unmarshal(data, &config)
	if err != nil {
		log.Println("error unmarshal config file: ", err)
		log.Println("returning default configuration")
		return setDefaults(), nil
	}

	return &config, nil
}

func setDefaults() *Configuration {
	return &Configuration{
		AIApiKey:              "",
		AIEndpoint:            "http://localhost:1234/v1/chat/completions",
		AIModel:               "llama-3.2-3b-instruct",
		AIResponseTimeoutSec:  60,
		KafkaBrokers:          []string{"localhost:9092"},
		KafkaConsumerTopics:   []string{"Request"},
		KafkaConsumerClientID: "request-consumer-1",
		KafkaConsumerGroup:    "request-consumer-group",
		KafkaProducerTopics:   []string{"Response"},
		KafkaProducerClientID: "response-producer-1",
		LogLevel:              "info",
	}
}

// Validate проверяет корректность конфигурации
func (c *Configuration) Validate() error {
	var errors error

	if c.AIEndpoint == "" {
		errors = multierr.Append(errors, fmt.Errorf("missing 'ai_endpoint' field"))
	}
	if c.AIModel == "" {
		errors = multierr.Append(errors, fmt.Errorf("missing 'ai_model' field"))
	}

	if err := c.validateKafka(); err != nil {
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
