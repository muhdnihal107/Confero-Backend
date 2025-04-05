# room_service/asgi.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'room_service.settings')
django.setup()
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from rooms.middleware import JWTAuthMiddleware
import rooms.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(
            rooms.routing.websocket_urlpatterns
        )
    ),
})