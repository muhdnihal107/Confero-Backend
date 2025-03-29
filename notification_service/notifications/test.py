import pika
import json

credentials = pika.PlainCredentials("admin", "adminpassword")
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="rabbitmq", port=5672, credentials=credentials)
)
channel = connection.channel()
channel.queue_declare(queue="notification_queue", durable=True)

test_message = {
    "receiver_id": "1",
    "message": "Test notification",
    "type": "friend_request",
    "friend_request_id": "123"
}
channel.basic_publish(
    exchange="",
    routing_key="notification_queue",
    body=json.dumps(test_message)
)
print("Test message sent!")
connection.close()