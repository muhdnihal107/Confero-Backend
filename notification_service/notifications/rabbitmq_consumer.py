from utils.rabbitmq import RabbitMQClient
import pika
import json
from django.conf import settings
from .models import Notification


def setup_rabbitmq_queues():
    rabbitmq_client = RabbitMQClient()
    rabbitmq_client.connect()
    
    #declare queues for notifications
    rabbitmq_client.declare_queue("friend_request_notifications")
    rabbitmq_client.declare_queue("room_invite_notifications")
    rabbitmq_client.declare_queue("public_room_notifications")
    
    return rabbitmq_client

if __name__ == "__main__":
    setup_rabbitmq_queues()
    
# notification_service/rabbitmq_consumer.py


def callback(ch, method, properties, body):
    message = json.loads(body)
    if message['type'] == 'friend_request':
        sender_email = message['sender_email']
        receiver_id = message['receiver_id']
        friend_request_id = message['friend_request_id']

        # Create notification
        notification = Notification(
            user_id=receiver_id,
            notification_type='friend_request',
            message=f"{sender_email} sent you a friend request (ID: {friend_request_id})"
        )
        notification.save()
        print(f"Notification created for user {receiver_id}")

    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consumer():
    credentials = pika.PlainCredentials('admin', 'adminpassword')
    parameters = pika.ConnectionParameters(
        host='rabbitmq',
        port=5672,
        virtual_host='/',
        credentials=credentials
    )
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.queue_declare(queue='friend_request_notifications', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='friend_request_notifications', on_message_callback=callback)

    print("Starting RabbitMQ consumer...")
    channel.start_consuming()

if __name__ == "__main__":
    start_consumer()
