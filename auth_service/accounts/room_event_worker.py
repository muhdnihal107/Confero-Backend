import json
from utils.rabbitmq import RabbitMQClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_room_event(ch, method, properties, body):
    message = json.loads(body.decode())
    event = message['event']
    if event == 'user_joined':
        room_id = message['room_id']
        room_name = message['room_name']
        user_email = message['user_email']
        logger.info(f"User {user_email} joined room {room_name} (ID: {room_id})")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_room_event_worker():
    rabbitmq_client = RabbitMQClient()
    rabbitmq_client.connect()
    rabbitmq_client.declare_queue('room_events')
    rabbitmq_client.consume_messages('room_events', process_room_event)

if __name__ == "__main__":
    start_room_event_worker()