# auth_service/rabbitmq_consumer.py
import pika
import json
from django.conf import settings
import jwt
from rest_framework_simplejwt.tokens import AccessToken

def validate_token(token):
    try:
        # Verify token (assuming you're using SimpleJWT)
        access_token = AccessToken(token)
        return {'status': 'success', 'user_id': access_token['user_id']}
    except jwt.InvalidTokenError:
        return {'status': 'error', 'message': 'Invalid token'}

def callback(ch, method, props, body):
    data = json.loads(body.decode())
    token = data.get('token')
    response = validate_token(token)

    # Send response back to notification_service
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD),
            virtual_host=settings.RABBITMQ_VHOST
        )
    )
    channel = connection.channel()
    channel.basic_publish(
        exchange='',
        routing_key=props.reply_to,
        body=json.dumps(response).encode(),
        properties=pika.BasicProperties(
            correlation_id=props.correlation_id
        )
    )
    connection.close()

def start_consuming():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD),
            virtual_host=settings.RABBITMQ_VHOST
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue='auth_request_queue', durable=True)
    channel.basic_consume(queue='auth_request_queue', on_message_callback=callback, auto_ack=True)
    print(" [*] Waiting for messages in auth_service...")
    channel.start_consuming()

if __name__ == "__main__":
    start_consuming()

