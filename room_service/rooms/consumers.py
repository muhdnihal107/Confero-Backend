import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync
from .models import Room
from .utils.rabbitmq import publish_to_rabbitmq

logger = logging.getLogger(__name__)

class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"room_{self.room_id}"

        # Check if user is authenticated
        if not self.scope['user'].is_authenticated:
            logger.warning(f"Unauthenticated connection attempt to room {self.room_id}")
            await self.close(code=4001)  # Custom close code for auth failure
            return

        # Verify room exists and user is authorized
        if not await self.check_room_and_user():
            logger.warning(f"Unauthorized access to room {self.room_id} by {self.scope['user'].email}")
            await self.close(code=4003)  # Custom close code for unauthorized
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f"User {self.scope['user'].email} connected to room {self.room_id}")

        # Add participant and publish event
        try:
            room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
            await database_sync_to_async(room.add_participant)(self.scope['user'].email)
            async_to_sync(publish_to_rabbitmq)('user_joined', self.room_id, self.scope['user'].email)
        except Exception as e:
            logger.error(f"Error adding participant or publishing event: {str(e)}")

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Remove participant and publish event (if authenticated)
        if self.scope['user'].is_authenticated:
            try:
                room = await database_sync_to_async(Room.objects.get)(id=self.room_id)
                await database_sync_to_async(room.remove_participant)(self.scope['user'].email)
                async_to_sync(publish_to_rabbitmq)('user_left', self.room_id, self.scope['user'].email)
                logger.info(f"User {self.scope['user'].email} disconnected from room {self.room_id}")
            except Exception as e:
                logger.error(f"Error removing participant or publishing event: {str(e)}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            logger.debug(f"Received message type: {message_type} from {self.scope['user'].email}")

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

        sender = self.scope['user'].email
        logger.debug(f"Broadcasting chat message from {sender}: {message}")

        # Broadcast chat message to room group
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
        if not signal_data:
            logger.warning(f"Empty {signal_type} data received")
            return

        sender = self.scope['user'].email
        logger.debug(f"Broadcasting {signal_type} from {sender}")

        # Broadcast WebRTC signaling data to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': signal_type,
                'data': signal_data,
                'sender': sender,
            }
        )

    # Receive messages from room group
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender'],
        }))

    async def webrtc_offer(self, event):
        await self.send(text_data=json.dumps({
            'type': 'webrtc_offer',
            'data': event['data'],
            'sender': event['sender'],
        }))

    async def webrtc_answer(self, event):
        await self.send(text_data=json.dumps({
            'type': 'webrtc_answer',
            'data': event['data'],
            'sender': event['sender'],
        }))

    async def ice_candidate(self, event):
        await self.send(text_data=json.dumps({
            'type': 'ice_candidate',
            'data': event['data'],
            'sender': event['sender'],
        }))

    @database_sync_to_async
    def check_room_and_user(self):
        try:
            room = Room.objects.get(id=self.room_id)
            user_email = self.scope['user'].email
            user_id = self.scope['user'].id
            is_authorized = (room.creator_id == user_id or 
                             user_email in room.invited_users or 
                             room.visibility == 'public')
            if is_authorized:
                logger.debug(f"User {user_email} authorized for room {self.room_id}")
            return is_authorized
        except Room.DoesNotExist:
            logger.error(f"Room {self.room_id} does not exist")
            return False
        except Exception as e:
            logger.error(f"Error checking room/user: {str(e)}")
            return False