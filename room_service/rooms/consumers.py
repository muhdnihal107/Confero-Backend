# rooms/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync
from .models import Room
from django.contrib.auth.models import AnonymousUser
from .rabbitmq_consumer import publish_to_rabbitmq 

logger = logging.getLogger(__name__)

from types import SimpleNamespace  # just in case

class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"room_{self.room_id}"

        user = self.scope.get("user", AnonymousUser())
        if not getattr(user, 'is_authenticated', False):
            logger.warning(f"Unauthenticated connection attempt to room {self.room_id}")
            await self.close(code=4001)
            return

        if not await self.check_room_and_user():
            logger.warning(f"Unauthorized access to room {self.room_id} by {getattr(user, 'email', 'unknown')}")
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info(f"User {getattr(user, 'email', 'unknown')} connected to room {self.room_id}")

        try:
            room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
            user_email = getattr(user, 'email', None)
            if user_email:
                await database_sync_to_async(room.add_participant)(user_email)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_joined',
                        'user_email': user_email,
                    }
                )
                async_to_sync(publish_to_rabbitmq)('user_joined', self.room_id, user_email)
        except Exception as e:
            logger.error(f"Error adding participant or publishing event: {str(e)}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        user = self.scope.get("user", AnonymousUser())

        if getattr(user, 'is_authenticated', False):
            try:
                room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
                user_email = getattr(user, 'email', None)
                if user_email:
                    await database_sync_to_async(room.remove_participant)(user_email)
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'user_left',
                            'user_email': user_email,
                        }
                    )
                    async_to_sync(publish_to_rabbitmq)('user_left', self.room_id, user_email)
                    logger.info(f"User {user_email} disconnected from room {self.room_id}")
            except Exception as e:
                logger.error(f"Error removing participant or publishing event: {str(e)}")

    async def receive(self, text_data):
        user = self.scope.get("user", AnonymousUser())
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            logger.debug(f"Received message type: {message_type} from {getattr(user, 'email', 'unknown')}")

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'webrtc_offer':
                await self.handle_webrtc_signal(data, 'webrtc_offer')
            elif message_type == 'webrtc_answer':
                await self.handle_webrtc_signal(data, 'webrtc_answer')
            elif message_type == 'ice_candidate':
                await self.handle_webrtc_signal(data, 'ice_candidate')
            else:
                logger.warning(f"Unknown message type: {message_type}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {str(e)}")
            await self.send(text_data=json.dumps({'error': 'Invalid message format'}))

    async def handle_chat_message(self, data):
        message = data.get('message')
        if not message:
            logger.warning("Empty chat message received")
            return
        sender = getattr(self.scope['user'], 'email', 'anonymous')
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': sender,
            }
        )

    async def handle_webrtc_signal(self, data, signal_type):
        signal_data = data.get('data')
        target = data.get('target')
        if not signal_data:
            logger.warning(f"Empty {signal_type} data received")
            return
        sender = getattr(self.scope['user'], 'email', 'anonymous')
        logger.debug(f"Broadcasting {signal_type} from {sender}")

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': signal_type,
                'data': signal_data,
                'sender': sender,
                'target': target,
            }
        )

    # Group event handlers remain the same
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def webrtc_offer(self, event):
        if event.get('target') == getattr(self.scope['user'], 'email', None) or not event.get('target'):
            await self.send(text_data=json.dumps({
                'type': 'webrtc_offer',
                'data': event['data'],
                'sender': event['sender'],
            }))

    async def webrtc_answer(self, event):
        if event.get('target') == getattr(self.scope['user'], 'email', None) or not event.get('target'):
            await self.send(text_data=json.dumps({
                'type': 'webrtc_answer',
                'data': event['data'],
                'sender': event['sender'],
            }))

    async def ice_candidate(self, event):
        if event.get('target') == getattr(self.scope['user'], 'email', None) or not event.get('target'):
            await self.send(text_data=json.dumps({
                'type': 'ice_candidate',
                'data': event['data'],
                'sender': event['sender'],
            }))

    async def user_joined(self, event):
        await self.send(text_data=json.dumps(event))

    async def user_left(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def check_room_and_user(self):
        try:
            room = Room.objects.get(id=self.room_id)
            user = self.scope.get('user', AnonymousUser())
            user_email = getattr(user, 'email', None)
            user_id = getattr(user, 'id', None)
            return room.creator_id == user_id or \
                   (user_email and user_email in room.invited_users) or \
                   room.visibility == 'public'
        except Room.DoesNotExist:
            return False