# shared_code/rabbitmq.py
import pika
import json
from typing import Callable


class RabbitMQClient:
    def __init__(self, host='rabbitmq', user='guest', password='guest', queue_name='uploadreports-local'):
        self.host = host
        self.queue_name = queue_name
        self.connection = None
        self.channel = None
        self.user = user
        self.password = password

    def connect(self):
        """
        Establish connection to RabbitMQ.
        """
        credentials = pika.PlainCredentials(self.user, self.password)
        parameters = pika.ConnectionParameters(self.host, 5672, '/', credentials)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        # Declare queue to ensure it exists
        self.channel.queue_declare(queue=self.queue_name)

    def consume(self, callback: Callable):
        """
        Start consuming messages from the RabbitMQ queue.
        """
        if not self.connection or not self.channel:
            self.connect()

        def on_message(ch, method, properties, body):
            # Process the message by calling the provided callback function
            callback(body)

        # Subscribe to the queue
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=on_message, auto_ack=True)
        print(f"Waiting for messages in {self.queue_name}. To exit press CTRL+C")
        self.channel.start_consuming()

    def close(self):
        """
        Close the RabbitMQ connection.
        """
        if self.connection and self.channel:
            self.channel.close()
            self.connection.close()
