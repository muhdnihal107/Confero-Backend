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