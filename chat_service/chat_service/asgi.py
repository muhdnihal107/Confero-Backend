# chat_service/chat_service/asgi.py
import os
import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_service.settings')
django.setup()
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from chats.middleware import JWTAuthMiddleware
import chats.routing


application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AllowedHostsOriginValidator(
        JWTAuthMiddleware(
            URLRouter(chats.routing.websocket_urlpatterns)
        )
    ),
})