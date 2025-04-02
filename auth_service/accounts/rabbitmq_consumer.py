
import json
import pika
import os
import time
import django
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

django.setup()

from accounts.models import CustomUser

def process_message(ch, method, properties, body):
    user_request = json.loads(body)
    user_id = user_request.get("user_id")

    print(f"Auth Service: Processing request for user {user_id}")

    try:
        user = CustomUser.objects.get(id=user_id)
        user_data = {
            "id": user.id,
            "email": user.email,
        }
    except CustomUser.DoesNotExist:
        user_data = {"error": "User not found"}

    response = json.dumps(user_data)

    if properties.reply_to:
        ch.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
            body=response.encode(),
        )
        print(f"Auth Service: Sent response to {properties.reply_to}")

    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_rabbitmq_consumer():
    max_retries = 10
    retry_delay = 5  
    attempt = 0

    while attempt < max_retries:
        try:
            credentials = pika.PlainCredentials(
                os.getenv('RABBITMQ_USER', 'admin'),
                os.getenv('RABBITMQ_PASS', 'adminpassword')
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=os.getenv('RABBITMQ_HOST', 'rabbitmq'),
                    port=int(os.getenv('RABBITMQ_PORT', 5672)),
                    credentials=credentials,
                    virtual_host=os.getenv('RABBITMQ_VHOST', '/')
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue="auth_service_queue", durable=True)
            channel.basic_consume(queue="auth_service_queue", on_message_callback=process_message)

            print("✅ Auth Service: Waiting for messages...")
            channel.start_consuming()
            break  
        except pika.exceptions.AMQPConnectionError as e:
            attempt += 1
            print(f"Failed to connect to RabbitMQ (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                print("Max retries reached. RabbitMQ consumer failed to start.")
                raise
