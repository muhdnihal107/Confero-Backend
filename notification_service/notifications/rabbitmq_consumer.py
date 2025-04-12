#notitfications/rabbitmq_consumer.py
import json
import pika
import os
import sys
import django
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "notification_service.settings")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from notifications.models import Notification

def process_notification(ch, method, properties, body):
    try:
        print(f"📥 Received raw message: {body}")
        data = json.loads(body)
        receiver_id = data.get("receiver_id")
        message = data.get("message")
        notification_type = data.get("type")
        friend_request_id = data.get("friend_request_id")
        if not all([receiver_id, message, notification_type]):
            raise ValueError("Missing required fields in notification data")

        # Save to database
        notification = Notification.objects.create(
            user_id=receiver_id,
            message=message,
            notification_type=notification_type,
            friend_requestId=friend_request_id if friend_request_id else None
        )
        print(f"✅ Notification saved for user {receiver_id}")

        # Broadcast to WebSocket group
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'notifications_{receiver_id}',
            {
                'type': 'send_notification',
                'notification': {
                    'id': str(notification.id),
                    'message': notification.message,
                    'notification_type': notification.notification_type,
                    'is_read': notification.is_read,
                    'created_at': notification.created_at.isoformat(),
                    'friend_requestId': notification.friend_requestId
                }
            }
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"❌ Error processing notification: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_notification_consumer():
    try:
        credentials = pika.PlainCredentials(
            os.getenv("RABBITMQ_USER", "admin"),
            os.getenv("RABBITMQ_PASS", "adminpassword")
        )
        connection_params = pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
            port=int(os.getenv("RABBITMQ_PORT", 5672)),
            credentials=credentials
        )

        print(f"🔌 Connecting to RabbitMQ at {connection_params.host}:{connection_params.port}")
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()

        queue_name = "notification_queue"
        channel.queue_declare(queue=queue_name, durable=True)
        print(f"✅ Queue '{queue_name}' declared")

        channel.basic_consume(
            queue=queue_name,
            on_message_callback=process_notification
        )
        print("✅ Notification Service: Waiting for messages...")

        channel.start_consuming()

    except pika.exceptions.AMQPConnectionError as e:
        print(f"❌ Failed to connect to RabbitMQ: {e}")
    except Exception as e:
        print(f"❌ Error in notification consumer: {e}")
    finally:
        if "connection" in locals():
            connection.close()
            print("🔌 Connection closed")

if __name__ == "__main__":
    start_notification_consumer()