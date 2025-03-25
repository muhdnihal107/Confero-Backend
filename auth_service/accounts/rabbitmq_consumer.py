# # auth_service/rabbitmq_consumer.py
# import pika
# import json
# from django.conf import settings
# import jwt
# from rest_framework_simplejwt.tokens import AccessToken

# def validate_token(token):
#     try:
#         # Verify token (assuming you're using SimpleJWT)
#         access_token = AccessToken(token)
#         return {'status': 'success', 'user_id': access_token['user_id']}
#     except jwt.InvalidTokenError:
#         return {'status': 'error', 'message': 'Invalid token'}

# def callback(ch, method, props, body):
#     data = json.loads(body.decode())
#     token = data.get('token')
#     response = validate_token(token)

#     # Send response back to notification_service
#     connection = pika.BlockingConnection(
#         pika.ConnectionParameters(
#             host=settings.RABBITMQ_HOST,
#             port=settings.RABBITMQ_PORT,
#             credentials=pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD),
#             virtual_host=settings.RABBITMQ_VHOST
#         )
#     )
#     channel = connection.channel()
#     channel.basic_publish(
#         exchange='',
#         routing_key=props.reply_to,
#         body=json.dumps(response).encode(),
#         properties=pika.BasicProperties(
#             correlation_id=props.correlation_id
#         )
#     )
#     connection.close()

# def start_consuming():
#     connection = pika.BlockingConnection(
#         pika.ConnectionParameters(
#             host=settings.RABBITMQ_HOST,
#             port=settings.RABBITMQ_PORT,
#             credentials=pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD),
#             virtual_host=settings.RABBITMQ_VHOST
#         )
#     )
#     channel = connection.channel()
#     channel.queue_declare(queue='auth_request_queue', durable=True)
#     channel.basic_consume(queue='auth_request_queue', on_message_callback=callback, auto_ack=True)
#     print(" [*] Waiting for messages in auth_service...")
#     channel.start_consuming()

# if __name__ == "__main__":
#     start_consuming()

import pika
import json
import logging
from django.conf import settings
from .models import CustomUser
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)

class AuthConsumer:
    def __init__(self):
        self.connection = None
        self.channel = None

    def start_consuming(self):
        self._connect()
        self._setup_queues()
        logger.info("Auth Service: Waiting for authentication requests...")
        self.channel.start_consuming()

    def _connect(self):
        credentials = pika.PlainCredentials(
            settings.RABBITMQ['USER'],
            settings.RABBITMQ['PASSWORD']
        )
        parameters = pika.ConnectionParameters(
            host=settings.RABBITMQ['HOST'],
            port=settings.RABBITMQ['PORT'],
            virtual_host=settings.RABBITMQ['VHOST'],
            credentials=credentials
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

    def _setup_queues(self):
        # Queue for token validation requests
        self.channel.queue_declare(queue='auth_validation_queue', durable=True)
        self.channel.basic_consume(
            queue='auth_validation_queue',
            on_message_callback=self._handle_validation_request,
            auto_ack=True
        )

        # Queue for user info requests
        self.channel.queue_declare(queue='user_info_queue', durable=True)
        self.channel.basic_consume(
            queue='user_info_queue',
            on_message_callback=self._handle_user_info_request,
            auto_ack=True
        )

    def _handle_validation_request(self, ch, method, properties, body):
        try:
            data = json.loads(body)
            token = data.get('token')
            request_id = data.get('request_id')
            
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            email = access_token['email']
            
            response = {
                'valid': True,
                'user_id': user_id,
                'email': email,
                'request_id': request_id
            }
            
            # Publish response to the callback queue
            self.channel.basic_publish(
                exchange='',
                routing_key=properties.reply_to,
                body=json.dumps(response)
            )
            
        except Exception as e:
            error_response = {
                'valid': False,
                'error': str(e),
                'request_id': request_id
            }
            self.channel.basic_publish(
                exchange='',
                routing_key=properties.reply_to,
                body=json.dumps(error_response)
            )

    def _handle_user_info_request(self, ch, method, properties, body):
        try:
            data = json.loads(body)
            user_id = data.get('user_id')
            request_id = data.get('request_id')
            
            user = CustomUser.objects.get(id=user_id)
            profile = user.profile
            
            response = {
                'user_id': user.id,
                'email': user.email,
                'username': user.username,
                'profile_data': {
                    'phone_number': profile.phone_number,
                    'bio': profile.bio,
                    'profile_photo': profile.profile_photo.url if profile.profile_photo else None
                },
                'request_id': request_id
            }
            
            self.channel.basic_publish(
                exchange='',
                routing_key=properties.reply_to,
                body=json.dumps(response)
            )
            
        except Exception as e:
            error_response = {
                'error': str(e),
                'request_id': request_id
            }
            self.channel.basic_publish(
                exchange='',
                routing_key=properties.reply_to,
                body=json.dumps(error_response)
            )