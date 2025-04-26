import json
import logging
import redis.asyncio as redis
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room
from django.conf import settings

logger = logging.getLogger(__name__)

class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'room_{self.room_id}'
        self.user_email = self.scope['user'].email if self.scope['user'].is_authenticated else None

        if not self.user_email:
            logger.error(f"Unauthenticated user attempted to connect to room {self.room_id}")
            await self.close(code=1008, reason="Unauthenticated user")
            return

        # Verify room exists and user is a participant
        room = await self.get_room()
        if not room:
            logger.error(f"Room {self.room_id} does not exist")
            await self.close(code=1008, reason="Room does not exist")
            return
        if self.user_email not in room.participants:
            logger.error(f"User {self.user_email} is not a participant in room {self.room_id}")
            await self.close(code=1008, reason="Not a participant")
            return

        try:
            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            logger.info(f"User {self.user_email} connected to room {self.room_id}")

            # Notify others of new user
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_connected',
                    'userEmail': self.user_email,
                }
            )
        except Exception as e:
            logger.error(f"Error connecting to room {self.room_id}: {str(e)}")
            await self.close(code=1011, reason="Internal server error")
            return

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            try:
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_disconnected',
                        'userEmail': self.user_email,
                    }
                )
            except Exception as e:
                logger.error(f"Error disconnecting from room {self.room_id}: {str(e)}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_key = f"msg:{self.room_id}:{hash(str(data))}"  # Unique key for message

            # Skip duplicate check for join-room since it's handled in connect
            if data.get('event') != 'join-room' and await self.is_duplicate_message(message_key):
                logger.debug(f"Duplicate message ignored: {data}")
                return

            if data.get('event') == 'join-room':
                logger.debug(f"Join-room message received from {self.user_email}")
                # Already handled in connect
                pass
            elif data.get('type') in ['webrtc_offer', 'webrtc_answer', 'ice_candidate']:
                logger.debug(f"WebRTC signal received from {self.user_email}: {data['type']}")
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'signal',
                        'signal': data,
                    }
                )
            else:
                logger.warning(f"Unknown message type from {self.user_email}: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received from {self.user_email}: {e}")
        except Exception as e:
            logger.error(f"Error processing message from {self.user_email}: {e}")

    async def user_connected(self, event):
        try:
            await self.send(text_data=json.dumps({
                'event': 'user-connected',
                'userEmail': event['userEmail'],
            }))
        except Exception as e:
            logger.error(f"Error sending user_connected for {event['userEmail']}: {e}")

    async def user_disconnected(self, event):
        try:
            await self.send(text_data=json.dumps({
                'event': 'user-disconnected',
                'userEmail': event['userEmail'],
            }))
        except Exception as e:
            logger.error(f"Error sending user_disconnected for {event['userEmail']}: {e}")

    async def signal(self, event):
        try:
            await self.send(text_data=json.dumps(event['signal']))
        except Exception as e:
            logger.error(f"Error sending signal: {e}")

    @database_sync_to_async
    def get_room(self):
        try:
            return Room.objects.get(id=self.room_id)
        except Room.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error fetching room {self.room_id}: {e}")
            return None

    async def is_duplicate_message(self, message_key):
        try:
            # Use a separate Redis client for message deduplication
            redis_client = redis.Redis(
                host=settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0][0],
                port=settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0][1],
                decode_responses=True
            )
            async with redis_client.pipeline() as pipe:
                pipe.setex(message_key, 60, 1)  # Store for 60 seconds
                pipe.exists(message_key)
                _, exists = await pipe.execute()
            await redis_client.close()
            return exists > 1  # True if message already existed
        except Exception as e:
            logger.error(f"Error checking duplicate message {message_key}: {e}")
            return False  # Allow message if Redis fails