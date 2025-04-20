# config/asgi.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'video_service.settings')
django.setup()
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import call.routing
from call.authentication.websocket_auth import WebSocketJWTAuthMiddleware



application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": WebSocketJWTAuthMiddleware(
        URLRouter(
            call.routing.websocket_urlpatterns
        )
    ),
})