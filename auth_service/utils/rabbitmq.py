import pika
import json
import os

class RabbitMQClient:
    def __init__(self):
        self.host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
        self.port = int(os.getenv('RABBITMQ_PORT', 5672))
        self.username = os.getenv('RABBITMQ_USER', 'admin')
        self.password = os.getenv('RABBITMQ_PASS', 'adminpassword')
        self.connection = None
        self.channel = None

    def connect(self):
        credentials = pika.PlainCredentials(self.username, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=credentials
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

    def declare_queue(self, queue_name):
        self.channel.queue_declare(queue=queue_name, durable=True)

    def publish_message(self, queue_name, message):
        if not self.connection or self.connection.is_closed:
            self.connect()
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
        )

    def consume_messages(self, queue_name, callback):
        if not self.connection or self.connection.is_closed:
            self.connect()
        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
        self.channel.start_consuming()

    def close(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()

# import pika
# import json
# from django.conf import settings

# class RabbitMQClient:
#     def __init__(self):
#         self.connection = None
#         self.channel = None

#     def connect(self):
#         credentials = pika.PlainCredentials(
#             settings.RABBITMQ['USER'], 
#             settings.RABBITMQ['PASSWORD']
#         )
#         parameters = pika.ConnectionParameters(
#             host=settings.RABBITMQ['HOST'],
#             port=settings.RABBITMQ['PORT'],
#             virtual_host=settings.RABBITMQ['VHOST'],
#             credentials=credentials
#         )
#         self.connection = pika.BlockingConnection(parameters)
#         self.channel = self.connection.channel()
#         return self.channel

#     def publish_message(self, queue_name, message):
#         self.channel.queue_declare(queue=queue_name, durable=True)
#         self.channel.basic_publish(
#             exchange='',
#             routing_key=queue_name,
#             body=json.dumps(message),
#             properties=pika.BasicProperties(
#                 delivery_mode=2,  # make message persistent
#             )
#         )

#     def close(self):
#         if self.connection and not self.connection.is_closed:
#             self.connection.close()