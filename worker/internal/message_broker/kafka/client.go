package kafk

import (
	"context"
	"encoding/json"
	"example.com/bot_worker/pkg/config"
	"example.com/bot_worker/pkg/models"
	"fmt"
	"log"
	"time"

	"github.com/IBM/sarama"
	"github.com/google/uuid"
)

type Client struct {
	producer sarama.SyncProducer
	consumer sarama.Consumer
	ctx      context.Context
}

func NewClient(ctx context.Context) (*Client, error) {
	var cfg = ctx.Value("config").(*config.Configuration)

	producerConfig := sarama.NewConfig()
	producerConfig.Producer.RequiredAcks = sarama.WaitForAll
	producerConfig.Producer.Retry.Max = 5
	producerConfig.Producer.Return.Successes = true
	producerConfig.Producer.Compression = sarama.CompressionSnappy
	producerConfig.Net.DialTimeout = 10 * time.Second

	producer, err := sarama.NewSyncProducer(cfg.KafkaBrokers, producerConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create Kafka producer: %w", err)
	}

	consumerConfig := sarama.NewConfig()
	consumerConfig.Consumer.Return.Errors = true
	consumerConfig.Consumer.Offsets.Initial = sarama.OffsetNewest
	consumerConfig.Net.DialTimeout = 10 * time.Second

	consumer, err := sarama.NewConsumer(cfg.KafkaBrokers, consumerConfig)
	if err != nil {
		_ = producer.Close()
		return nil, fmt.Errorf("failed to create Kafka consumer: %w", err)
	}

	return &Client{
		producer: producer,
		consumer: consumer,
		ctx:      ctx,
	}, nil
}

func (c *Client) SendRequest() (<-chan models.Response, error) {
	userID := uuid.New().String()
	chatID := uuid.New().String()

	req := models.Request{
		UserID:     userID,
		ChatID:     chatID,
		FileFormat: "excel",
		FileURL:    "http://192.168.3.92:9001/api/v1/download-shared-object/aHR0cDovLzEyNy4wLjAuMTo5MDAwL3Rlc3QvbmFiZWJhJTIwJTI4MSUyOS54bHN4P1gtQW16LUFsZ29yaXRobT1BV1M0LUhNQUMtU0hBMjU2JlgtQW16LUNyZWRlbnRpYWw9RFhCWkNRTURJUUxON0xJRjlMNFMlMkYyMDI2MDQxMyUyRnVzLWVhc3QtMSUyRnMzJTJGYXdzNF9yZXF1ZXN0JlgtQW16LURhdGU9MjAyNjA0MTNUMTEyMjU5WiZYLUFtei1FeHBpcmVzPTQzMjAwJlgtQW16LVNlY3VyaXR5LVRva2VuPWV5SmhiR2NpT2lKSVV6VXhNaUlzSW5SNWNDSTZJa3BYVkNKOS5leUpoWTJObGMzTkxaWGtpT2lKRVdFSmFRMUZOUkVsUlRFNDNURWxHT1V3MFV5SXNJbVY0Y0NJNk1UYzNOakV5TWpVM05Td2ljR0Z5Wlc1MElqb2lkWE5sY2lKOS52bzhSTFVISk1YNDVDZ1ZDQVZCZ1NWRmlfMlVHMTlGT0FFTHhPVjR4cjRBMm04c3NmRzI2VXFSa2hNZk9vQkpiTU9UTW5vMEZpUUFlcDBtV1hLdWYwQSZYLUFtei1TaWduZWRIZWFkZXJzPWhvc3QmdmVyc2lvbklkPW51bGwmWC1BbXotU2lnbmF0dXJlPTUzNDliYTc0NjgxNzRlMzE1ZTY1OTNlODkxYjhjNmQxYTNlZDkzYzRkYmJmYzJjMjkzZGI4OTY4NDNhZTEzYjA",
		Prompt:     "Какой балл у Голика",
		Attempt:    0,
	}

	jsonData, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}
	respChan := make(chan models.Response, 1)

	go c.waitForResponse(userID, respChan)

	msg := &sarama.ProducerMessage{
		Topic: "request",
		Key:   sarama.StringEncoder(userID),
		Value: sarama.ByteEncoder(jsonData),
		Headers: []sarama.RecordHeader{
			{Key: []byte("timestamp"), Value: []byte(time.Now().String())},
			{Key: []byte("type"), Value: []byte("request")},
		},
	}

	partition, offset, err := c.producer.SendMessage(msg)
	if err != nil {
		close(respChan)
		return nil, fmt.Errorf("failed to send request: %w", err)
	}

	log.Printf("Request sent: %s, partition: %d, offset: %d", userID, partition, offset)

	return respChan, nil
}

func (c *Client) waitForResponse(userID string, respChan chan models.Response) {
	defer close(respChan)

	partitionConsumer, err := c.consumer.ConsumePartition("response", 0, sarama.OffsetNewest)
	if err != nil {
		log.Printf("Failed to consume partition: %v", err)
		return
	}
	defer func() { _ = partitionConsumer.Close() }()

	log.Printf("Waiting for response for request %s", userID)

	timeout := time.After(30 * time.Second)

	for {
		select {
		case <-c.ctx.Done():
			log.Printf("Context cancelled while waiting for response %s", userID)
			return

		case <-timeout:
			log.Printf("Timeout waiting for response %s", userID)
			return

		case msg := <-partitionConsumer.Messages():

			var resp models.Response
			if err = json.Unmarshal(msg.Value, &resp); err != nil {
				log.Printf("Failed to unmarshal response: %v", err)
				continue
			}

			if resp.UserID == userID {
				log.Printf("Received response for request %s", userID)
				respChan <- resp
				return
			}
		case err = <-partitionConsumer.Errors():
			log.Printf("Consumer error: %v", err)
		}
	}
}

func (c *Client) Close() error {
	if c.producer != nil {
		_ = c.producer.Close()
	}
	if c.consumer != nil {
		_ = c.consumer.Close()
	}
	return nil
}

func TestClient(ctx context.Context) {
	time.Sleep(3 * time.Second)
	client, err := NewClient(ctx)
	if err != nil {
		log.Fatalf("Failed to create Kafka client: %v", err)
	}
	defer func() {
		_ = client.Close()
	}()

	time.Sleep(1 * time.Second)

	go func() {
		respChan, err := client.SendRequest()
		if err != nil {
			log.Printf("Failed to send request: %v", err)
			return
		}

		select {
		case resp := <-respChan:
			fmt.Printf("Response received: %+v\n", resp)
		case <-time.After(30 * time.Second):
			fmt.Println("Timeout waiting for response")
		}
	}()

	time.Sleep(10 * time.Second)
	fmt.Println("\nProgram finished")
}
