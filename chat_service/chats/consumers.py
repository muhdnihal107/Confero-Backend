import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from chats.models import ChatGroup,Message
from chats.utils import validate_user,are_friends