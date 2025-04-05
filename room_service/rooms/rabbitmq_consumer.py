

import pika
import json
import os
import logging

logger = logging.getLogger(__name__)

def publish_to_rabbitmq(event_type, room_id, user_email):
    """
    Publish an event to RabbitMQ for inter-service communication.
    
    Args:
        event_type (str): The type of event (e.g., 'user_joined', 'user_left').
        room_id (str): The ID of the room.
        user_email (str): The email of the user involved in the event.
    """
    try:
        # Get RabbitMQ configuration from environment variables
        rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
        rabbitmq_port = int(os.getenv('RABBITMQ_PORT', 5672))
        rabbitmq_user = os.getenv('RABBITMQ_USER', 'admin')
        rabbitmq_pass = os.getenv('RABBITMQ_PASS', 'adminpassword')

        # Establish connection
        credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=rabbitmq_host,
                port=rabbitmq_port,
                credentials=credentials
            )
        )
        channel = connection.channel()

        # Declare queue (durable to persist across restarts)
        channel.queue_declare(queue='notifications', durable=True)

        # Create message payload
        message = json.dumps({
            'event_type': event_type,
            'room_id': room_id,
            'user_email': user_email
        })

        # Publish message
        channel.basic_publish(
            exchange='',  # Default exchange
            routing_key='notifications',  # Queue name
            body=message,
            properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
        )
        logger.info(f"Published {event_type} event for {user_email} in room {room_id} to RabbitMQ")

        # Close connection
        connection.close()

    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error publishing to RabbitMQ: {str(e)}")
        raise

# # rooms/rabbitmq_consumer.py
# import json
# import pika
# import os
# import sys
# import django
# from django.conf import settings
# from asgiref.sync import async_to_sync
# from channels.layers import get_channel_layer

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "room_service.settings")
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# django.setup()

# from rooms.models import Room

# def process_room_event(ch, method, properties, body):
#     try:
#         print(f"📥 Received raw message: {body}")
#         data = json.loads(body)
#         event = data.get("event")
#         room_id = data.get("room_id")
#         user_email = data.get("user_email")

#         if event not in ["user_joined", "user_left"]:
#             raise ValueError("Unknown event type")

#         room = Room.objects.get(id=room_id)
#         channel_layer = get_channel_layer()

#         if event == "user_joined":
#             room.add_participant(user_email)
#             async_to_sync(channel_layer.group_send)(
#                 f"room_{room_id}",
#                 {"type": "user_joined", "user_email": user_email}
#             )
#         elif event == "user_left":
#             room.remove_participant(user_email)
#             async_to_sync(channel_layer.group_send)(
#                 f"room_{room_id}",
#                 {"type": "user_left", "user_email": user_email}
#             )

#         ch.basic_ack(delivery_tag=method.delivery_tag)
#     except Exception as e:
#         print(f"❌ Error processing room event: {e}")
#         ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

# def start_room_consumer():
#     credentials = pika.PlainCredentials(
#         os.getenv("RABBITMQ_USER", "admin"),
#         os.getenv("RABBITMQ_PASS", "adminpassword")
#     )
#     connection = pika.BlockingConnection(
#         pika.ConnectionParameters(
#             host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
#             port=int(os.getenv("RABBITMQ_PORT", 5672)),
#             credentials=credentials
#         )
#     )
#     channel = connection.channel()
#     channel.queue_declare(queue="room_events", durable=True)
#     channel.basic_consume(queue="room_events", on_message_callback=process_room_event)
#     print("✅ Room Service: Waiting for RabbitMQ messages...")
#     channel.start_consuming()

# if __name__ == "__main__":
#     start_room_consumer()