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
	reqID := uuid.New().String()
	userID := uuid.New().String()

	req := models.Request{
		TaskID:  reqID,
		UserID:  userID,
		FileURL: "http://192.168.3.92:9001/api/v1/download-shared-object/aHR0cDovLzEyNy4wLjAuMTo5MDAwL2JvdHdvcmtlcmRhdGEvJUQwJTlEJUQwJUIwJUQwJUIxJUQwJUI1JUQwJUIxJUQwJUI4JUQwJUJELTExJTIwJUQwJTlFJUQxJTg2JUQwJUI1JUQwJUJEJTIwJUQwJUJEJUQwJUI1JUQwJUI0JUQwJUI1JUQwJUJCJTIwMjAyNS0yNiUyMCVEMCU5RSVEMSU4MSVEMCVCNSVEMCVCRCVEMSU4QyUyMCUyODIlMjklMjAlMjgxJTI5Lnhsc3g_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1CMlMzWTJFVjJCOUhQRTAwSThEWSUyRjIwMjYwMjI0JTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI2MDIyNFQxNzU0NDNaJlgtQW16LUV4cGlyZXM9NDMyMDAmWC1BbXotU2VjdXJpdHktVG9rZW49ZXlKaGJHY2lPaUpJVXpVeE1pSXNJblI1Y0NJNklrcFhWQ0o5LmV5SmhZMk5sYzNOTFpYa2lPaUpDTWxNeldUSkZWakpDT1VoUVJUQXdTVGhFV1NJc0ltVjRjQ0k2TVRjM01UazVPRFkyT1N3aWNHRnlaVzUwSWpvaWRYTmxjaUo5LllPTE5wbWREZFRZWTFvbVgtcW45MVlxcGJRS0dhNWxuMXFrelQzQUtLc0xhNG45UHhVSlRvX1ZtNi1sNVF1TE51VFBNYlVFSEl4WmVPTFBoRW93aDZRJlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCZ2ZXJzaW9uSWQ9bnVsbCZYLUFtei1TaWduYXR1cmU9YTFkNWFjOTFjZTg1MjEwNTU0ODNlNWFjODVlNzY5MzFmZGM2YTYxNGUxODJiOWU3YzBhYWFmZDMxODE0NjljZA",
		Prompt:  "Как учится Голик",
	}

	jsonData, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}
	respChan := make(chan models.Response, 1)

	go c.waitForResponse(reqID, respChan)

	msg := &sarama.ProducerMessage{
		Topic: "request",
		Key:   sarama.StringEncoder(reqID),
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

	log.Printf("Request sent: %s, partition: %d, offset: %d", reqID, partition, offset)

	return respChan, nil
}

func (c *Client) waitForResponse(reqID string, respChan chan models.Response) {
	defer close(respChan)

	partitionConsumer, err := c.consumer.ConsumePartition("response", 0, sarama.OffsetNewest)
	if err != nil {
		log.Printf("Failed to consume partition: %v", err)
		return
	}
	defer func() { _ = partitionConsumer.Close() }()

	log.Printf("Waiting for response for request %s", reqID)

	timeout := time.After(30 * time.Second)

	for {
		select {
		case <-c.ctx.Done():
			log.Printf("Context cancelled while waiting for response %s", reqID)
			return

		case <-timeout:
			log.Printf("Timeout waiting for response %s", reqID)
			return

		case msg := <-partitionConsumer.Messages():

			var resp models.Response
			if err := json.Unmarshal(msg.Value, &resp); err != nil {
				log.Printf("Failed to unmarshal response: %v", err)
				continue
			}

			if resp.TaskID == reqID {
				log.Printf("Received response for request %s", reqID)
				respChan <- resp
				return
			}
		case err := <-partitionConsumer.Errors():
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
		case <-time.After(5 * time.Second):
			fmt.Println("Timeout waiting for response")
		}
	}()

	time.Sleep(10 * time.Second)
	fmt.Println("\nProgram finished")
}
