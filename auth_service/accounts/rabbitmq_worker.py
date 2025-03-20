import json
from utils.rabbitmq import RabbitMQClient
from rest_framework_simplejwt.tokens import AccessToken

def process_validation_request(ch, method, properties, body):
    message = json.loads(body.decode())
    token = message['token']
    request_id = message['request_id']

    rabbitmq_client = RabbitMQClient()
    rabbitmq_client.connect()

    try:
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        email = access_token['email']
        response = {
            'valid': True,
            'user_id': user_id,
            'email': email,
            'request_id': request_id
        }
    except Exception as e:
        response = {
            'valid': False,
            'error': str(e),
            'request_id': request_id
        }

    rabbitmq_client.publish_message('auth_response_queue', response)
    rabbitmq_client.close()
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_worker():
    rabbitmq_client = RabbitMQClient()
    rabbitmq_client.connect()
    rabbitmq_client.declare_queue('auth_request_queue')
    rabbitmq_client.consume_messages('auth_request_queue', process_validation_request)

if __name__ == "__main__":
    start_worker()