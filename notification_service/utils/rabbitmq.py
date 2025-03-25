# import pika
# import json
# import os

# class RabbitMQClient:
#     def __init__(self):
#         self.host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
#         self.port = int(os.getenv('RABBITMQ_PORT', 5672))
#         self.username = os.getenv('RABBITMQ_USER', 'admin')
#         self.password = os.getenv('RABBITMQ_PASS', 'adminpassword')
#         self.connection = None
#         self.channel = None

#     def connect(self):
#         credentials = pika.PlainCredentials(self.username, self.password)
#         parameters = pika.ConnectionParameters(
#             host=self.host,
#             port=self.port,
#             credentials=credentials
#         )
#         self.connection = pika.BlockingConnection(parameters)
#         self.channel = self.connection.channel()

#     def declare_queue(self, queue_name):
#         self.channel.queue_declare(queue=queue_name, durable=True)

#     def publish_message(self, queue_name, message):
#         if not self.connection or self.connection.is_closed:
#             self.connect()
#         self.channel.basic_publish(
#             exchange='',
#             routing_key=queue_name,
#             body=json.dumps(message),
#             properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
#         )

#     def consume_messages(self, queue_name, callback):
#         if not self.connection or self.connection.is_closed:
#             self.connect()
#         self.channel.queue_declare(queue=queue_name, durable=True)
#         self.channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
#         self.channel.start_consuming()

#     def close(self):
#         if self.connection and not self.connection.is_closed:
#             self.connection.close()
            
            
            
# notification_service/utils/rabbitmq.py
import pika
import uuid
import json
from django.conf import settings

class RabbitMQClient:
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                credentials=pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD),
                virtual_host=settings.RABBITMQ_VHOST
            )
        )
        self.channel = self.connection.channel()
        self.callback_queue = self.channel.queue_declare(queue='', exclusive=True).method.queue
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True
        )
        self.response = None
        self.corr_id = None

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = json.loads(body.decode())

    def validate_token(self, token):
        self.response = None
        self.corr_id = str(uuid.uuid4())

        # Send token to auth_service
        self.channel.queue_declare(queue='auth_request_queue', durable=True)
        self.channel.basic_publish(
            exchange='',
            routing_key='auth_request_queue',
            body=json.dumps({'token': token}).encode(),
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            )
        )

        # Wait for response
        while self.response is None:
            self.connection.process_data_events(time_limit=1)  # Timeout after 1 second
        return self.response

    def close(self):
        self.connection.close()