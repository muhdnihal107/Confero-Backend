# call/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/conference/(?P<conference_id>\w+)/$', consumers.VideoCallConsumer.as_asgi()),
]