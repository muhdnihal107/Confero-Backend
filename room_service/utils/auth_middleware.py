import uuid
import time
from django.http import JsonResponse
from utils.rabbitmq import RabbitMQClient

class TokenValidationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.rabbitmq_client = RabbitMQClient()
        self.rabbitmq_client.connect()
        self.rabbitmq_client.declare_queue('auth_request_queue')
        self.rabbitmq_client.declare_queue('auth_response_queue')
        self.responses = {}

    def __call__(self, request):
        # Skip authentication for public endpoints if needed
        if request.path.startswith('/api/public-rooms/'):
            return self.get_response(request)

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({"error": "Authorization header missing or invalid"}, status=401)

        token = auth_header.split(' ')[1]
        request_id = str(uuid.uuid4())

        # Send token validation request to Auth Service via RabbitMQ
        self.rabbitmq_client.publish_message(
            queue_name='auth_request_queue',
            message={
                'token': token,
                'request_id': request_id
            }
        )

        # Consume the response
        def callback(ch, method, properties, body):
            response = json.loads(body.decode())
            if response['request_id'] == request_id:
                self.responses[request_id] = response
                ch.basic_ack(delivery_tag=method.delivery_tag)

        self.rabbitmq_client.channel.basic_consume(
            queue='auth_response_queue',
            on_message_callback=callback
        )

        # Wait for the response (with a timeout)
        timeout = 5  # seconds
        start_time = time.time()
        while request_id not in self.responses:
            if time.time() - start_time > timeout:
                return JsonResponse({"error": "Authentication timeout"}, status=503)
            self.rabbitmq_client.channel.connection.process_data_events(time_limit=1)

        response = self.responses.pop(request_id)
        if not response['valid']:
            return JsonResponse({"error": "Invalid token", "detail": response.get('error')}, status=401)

        # Attach user info to the request
        request.user = type('User', (), {
            'id': response['user_id'],
            'email': response['email']
        })()

        return self.get_response(request)

    def __del__(self):
        self.rabbitmq_client.close()