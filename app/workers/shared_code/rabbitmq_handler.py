import pika
import json
from typing import Callable
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RabbitMQClient:
    def __init__(self, host='rabbitmq', user='guest', password='guest', queue_name='uploadreports-local'):
        self.host = host
        self.queue_name = queue_name
        self.connection = None
        self.channel = None
        self.user = user
        self.password = password
        logger.info(f"Initialized RabbitMQClient with host={host}, queue_name={queue_name}")

    def connect(self):
        """
        Establish connection to RabbitMQ.
        """
        try:
            logger.info(f"Connecting to RabbitMQ at {self.host}...")
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(self.host, 5672, '/', credentials)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Declare queue to ensure it exists
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            logger.info(f"Successfully connected to RabbitMQ and declared queue {self.queue_name}.")
        except Exception as e:
            logger.error(f"Error connecting to RabbitMQ: {e}", exc_info=True)
            raise

    def consume(self, callback: Callable):
        """
        Start consuming messages from the RabbitMQ queue.
        """
        if not self.connection or not self.channel:
            logger.info("Connection or channel not found, establishing new connection...")
            self.connect()

        def on_message(ch, method, properties, body):
            # Process the message by calling the provided callback function
            logger.info(f"Received message from queue {self.queue_name}.")
            callback(body)

        # Subscribe to the queue
        logger.info(f"Starting to consume messages from queue {self.queue_name}...")
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=on_message, auto_ack=True)
        logger.info(f"Waiting for messages in {self.queue_name}. To exit press CTRL+C")
        self.channel.start_consuming()

    def close(self):
        """
        Close the RabbitMQ connection.
        """
        if self.connection and self.channel:
            try:
                logger.info("Closing RabbitMQ connection and channel...")
                self.channel.close()
                self.connection.close()
                logger.info("RabbitMQ connection and channel closed.")
            except Exception as e:
                logger.error(f"Error closing RabbitMQ connection: {e}", exc_info=True)
