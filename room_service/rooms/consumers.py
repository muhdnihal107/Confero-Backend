# import json
# import logging
# import redis.asyncio as redis
# from channels.generic.websocket import AsyncWebsocketConsumer
# from channels.db import database_sync_to_async
# from .models import Room
# from django.conf import settings

# logger = logging.getLogger(__name__)

# class RoomConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_id = self.scope['url_route']['kwargs']['room_id']
#         self.room_group_name = f'room_{self.room_id}'
#         self.user_email = self.scope['user'].email if self.scope['user'].is_authenticated else None

#         if not self.user_email:
#             logger.error(f"Unauthenticated user attempted to connect to room {self.room_id}")
#             await self.close(code=1008, reason="Unauthenticated user")
#             return

#         room = await self.get_room()
#         if not room:
#             logger.error(f"Room {self.room_id} does not exist")
#             await self.close(code=1008, reason="Room does not exist")
#             return
#         if self.user_email not in room.participants:
#             logger.error(f"User {self.user_email} is not a participant in room {self.room_id}")
#             await self.close(code=1008, reason="Not a participant")
#             return

#         try:
#             await self.channel_layer.group_add(self.room_group_name, self.channel_name)
#             await self.accept()
#             logger.info(f"User {self.user_email} connected to room {self.room_id}")

#             await self.channel_layer.group_send(
#                 self.room_group_name,
#                 {
#                     'type': 'user_connected',
#                     'userEmail': self.user_email,
#                     'sender_channel': self.channel_name,
#                 }
#             )
#         except Exception as e:
#             logger.error(f"Error connecting to room {self.room_id}: {str(e)}")
#             await self.close(code=1011, reason="Internal server error")
#             return

#     async def disconnect(self, close_code):
#         if hasattr(self, 'room_group_name'):
#             try:
#                 await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
#                 await self.channel_layer.group_send(
#                     self.room_group_name,
#                     {
#                         'type': 'user_disconnected',
#                         'userEmail': self.user_email,
#                         'sender_channel': self.channel_name,
#                     }
#                 )
#                 logger.info(f"User {self.user_email} disconnected from room {self.room_id}, code: {close_code}")
#             except Exception as e:
#                 logger.error(f"Error disconnecting from room {self.room_id}: {str(e)}")

#     async def receive(self, text_data):
#         try:
#             data = json.loads(text_data)
#             message_key = f"msg:{self.room_id}:{hash(str(data))}"

#             if data.get('event') != 'join-room' and await self.is_duplicate_message(message_key):
#                 logger.debug(f"Duplicate message ignored from {self.user_email}: {data}")
#                 return

#             if data.get('event') == 'join-room':
#                 logger.debug(f"Join-room message received from {self.user_email}")
#             elif data.get('type') == 'chat_message':
#                 logger.debug(f"Chat message from {self.user_email}: {data['data']}")
#                 await self.channel_layer.group_send(
#                     self.room_group_name,
#                     {
#                         'type': 'chat_message',
#                         'message': {
#                             'type': 'chat_message',
#                             'data': data['data'],
#                             'sender': self.user_email,
#                             'timestamp': data.get('timestamp', ''),
#                         },
#                     }
#                 )
#             elif data.get('type') in ['webrtc_offer', 'webrtc_answer', 'ice_candidate']:
#                 logger.debug(f"WebRTC signal from {self.user_email}: {data['type']} to {data.get('target')}")
#                 await self.channel_layer.group_send(
#                     self.room_group_name,
#                     {
#                         'type': 'signal',
#                         'signal': data,
#                         'sender_channel': self.channel_name,
#                     }
#                 )
#             else:
#                 logger.warning(f"Unknown message type from {self.user_email}: {data}")
#         except json.JSONDecodeError as e:
#             logger.error(f"Invalid JSON received from {self.user_email}: {e}")
#         except Exception as e:
#             logger.error(f"Error processing message from {self.user_email}: {e}")

#     async def user_connected(self, event):
#         if event.get('sender_channel') != self.channel_name:
#             try:
#                 await self.send(text_data=json.dumps({
#                     'event': 'user-connected',
#                     'userEmail': event['userEmail'],
#                 }))
#                 logger.debug(f"Sent user_connected to {self.user_email} for {event['userEmail']}")
#             except Exception as e:
#                 logger.error(f"Error sending user_connected to {self.user_email}: {e}")

#     async def user_disconnected(self, event):
#         try:
#             await self.send(text_data=json.dumps({
#                 'event': 'user-disconnected',
#                 'userEmail': event['userEmail'],
#             }))
#             logger.debug(f"Sent user_disconnected to {self.user_email} for {event['userEmail']}")
#         except Exception as e:
#             logger.error(f"Error sending user_disconnected to {self.user_email}: {e}")

#     async def signal(self, event):
#         signal = event['signal']
#         if signal.get('target') == self.user_email or not signal.get('target'):
#             if event.get('sender_channel') != self.channel_name:
#                 try:
#                     await self.send(text_data=json.dumps(signal))
#                     logger.debug(f"Sent signal to {self.user_email}: {signal['type']}")
#                 except Exception as e:
#                     logger.error(f"Error sending signal to {self.user_email}: {e}")

#     async def chat_message(self, event):
#         try:
#             await self.send(text_data=json.dumps(event['message']))
#             logger.debug(f"Sent chat message to {self.user_email} from {event['message']['sender']}")
#         except Exception as e:
#             logger.error(f"Error sending chat message to {self.user_email}: {e}")

#     async def screen_share_state(self, event):
#         try:
#             await self.send(text_data=json.dumps(event['message']))
#             logger.debug(f"Sent screen share state to {self.user_email} from {event['message']['sender']}")
#         except Exception as e:
#             logger.error(f"Error sending screen share state to {self.user_email}: {e}")

#     @database_sync_to_async
#     def get_room(self):
#         try:
#             return Room.objects.get(id=self.room_id)
#         except Room.DoesNotExist:
#             return None
#         except Exception as e:
#             logger.error(f"Error fetching room {self.room_id}: {e}")
#             return None

#     async def is_duplicate_message(self, message_key):
#         try:
#             redis_client = redis.Redis(
#                 host=settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0][0],
#                 port=settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0][1],
#                 decode_responses=True
#             )
#             async with redis_client.pipeline() as pipe:
#                 pipe.setex(message_key, 60, 1)
#                 pipe.exists(message_key)
#                 _, exists = await pipe.execute()
#             await redis_client.close()
#             return exists > 1
#         except Exception as e:
#             logger.error(f"Error checking duplicate message {message_key}: {e}")
#             return False





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
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            logger.info(f"User {self.user_email} connected to room {self.room_id}")

            # Increment connection count and set room to live
            await self.increment_connection_count()

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_connected',
                    'userEmail': self.user_email,
                    'sender_channel': self.channel_name,
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
                        'sender_channel': self.channel_name,
                    }
                )
                logger.info(f"User {self.user_email} disconnected from room {self.room_id}, code:stabilize {close_code}")

                # Decrement connection count and update live status
                await self.decrement_connection_count()
            except Exception as e:
                logger.error(f"Error disconnecting from room {self.room_id}: {str(e)}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_key = f"msg:{self.room_id}:{hash(str(data))}"

            if data.get('event') != 'join-room' and await self.is_duplicate_message(message_key):
                logger.debug(f"Duplicate message ignored from {self.user_email}: {data}")
                return

            if data.get('event') == 'join-room':
                logger.debug(f"Join-room message received from {self.user_email}")
            elif data.get('type') == 'chat_message':
                logger.debug(f"Chat message from {self.user_email}: {data['data']}")
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': {
                            'type': 'chat_message',
                            'data': data['data'],
                            'sender': self.user_email,
                            'timestamp': data.get('timestamp', ''),
                        },
                    }
                )
            elif data.get('type') == 'heartbeat':
                logger.debug(f"Heartbeat from {self.user_email} in room {self.room_id}")
            elif data.get('type') in ['webrtc_offer', 'webrtc_answer', 'ice_candidate']:
                logger.debug(f"WebRTC signal from {self.user_email}: {data['type']} to {data.get('target')}")
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'signal',
                        'signal': data,
                        'sender_channel': self.channel_name,
                    }
                )
            elif data.get('type') == 'screen_share_state':
                logger.debug(f"Screen share state from {self.user_email}: {data['data']}")
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'screen_share_state',
                        'message': {
                            'type': 'screen_share_state',
                            'data': data['data'],
                            'sender': self.user_email,
                        },
                    }
                )
            else:
                logger.warning(f"Unknown message type from {self.user_email}: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received from {self.user_email}: {e}")
        except Exception as e:
            logger.error(f"Error processing message from {self.user_email}: {e}")

    async def user_connected(self, event):
        if event.get('sender_channel') != self.channel_name:
            try:
                await self.send(text_data=json.dumps({
                    'event': 'user-connected',
                    'userEmail': event['userEmail'],
                }))
                logger.debug(f"Sent user_connected to {self.user_email} for {event['userEmail']}")
            except Exception as e:
                logger.error(f"Error sending user_connected to {self.user_email}: {e}")

    async def user_disconnected(self, event):
        try:
            await self.send(text_data=json.dumps({
                'event': 'user-disconnected',
                'userEmail': event['userEmail'],
            }))
            logger.debug(f"Sent user_disconnected to {self.user_email} for {event['userEmail']}")
        except Exception as e:
            logger.error(f"Error sending user_disconnected to {self.user_email}: {e}")

    async def signal(self, event):
        signal = event['signal']
        if signal.get('target') == self.user_email or not signal.get('target'):
            if event.get('sender_channel') != self.channel_name:
                try:
                    await self.send(text_data=json.dumps(signal))
                    logger.debug(f"Sent signal to {self.user_email}: {signal['type']}")
                except Exception as e:
                    logger.error(f"Error sending signal to {self.user_email}: {e}")

    async def chat_message(self, event):
        try:
            await self.send(text_data=json.dumps(event['message']))
            logger.debug(f"Sent chat message to {self.user_email} from {event['message']['sender']}")
        except Exception as e:
            logger.error(f"Error sending chat message to {self.user_email}: {e}")

    async def screen_share_state(self, event):
        try:
            await self.send(text_data=json.dumps(event['message']))
            logger.debug(f"Sent screen share state to {self.user_email} from {event['message']['sender']}")
        except Exception as e:
            logger.error(f"Error sending screen share state to {self.user_email}: {e}")

    @database_sync_to_async
    def get_room(self):
        try:
            return Room.objects.get(id=self.room_id)
        except Room.DoesNotExist:
            logger.error(f"Room {self.room_id} does not exist")
            return None
        except Exception as e:
            logger.error(f"Error fetching room {self.room_id}: {e}")
            return None

    @database_sync_to_async
    def update_room_live_status(self, is_live):
        try:
            room = Room.objects.get(id=self.room_id)
            room.is_live = is_live
            room.save()
            logger.info(f"Room {self.room_id} is_live set to {is_live}")
        except Room.DoesNotExist:
            logger.error(f"Room {self.room_id} does not exist")
        except Exception as e:
            logger.error(f"Error updating live status for room {self.room_id}: {e}")

    async def increment_connection_count(self):
        redis_client = redis.Redis(
            host=settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0][0],
            port=settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0][1],
            decode_responses=True
        )
        try:
            count = await redis_client.incr(f"room:{self.room_id}:connections")
            logger.info(f"Incremented connection count for room {self.room_id} to {count}")
            # Set is_live to True on first connection
            if count == 1:
                await self.update_room_live_status(is_live=True)
        except Exception as e:
            logger.error(f"Error incrementing connection count for room {self.room_id}: {e}")
        finally:
            await redis_client.close()

    async def decrement_connection_count(self):
        redis_client = redis.Redis(
            host=settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0][0],
            port=settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0][1],
            decode_responses=True
        )
        try:
            count = await redis_client.decr(f"room:{self.room_id}:connections")
            logger.info(f"Decremented connection count for room {self.room_id} to {count}")
            # Set is_live to False if no connections remain
            if count <= 0:
                await self.update_room_live_status(is_live=False)
                await redis_client.delete(f"room:{self.room_id}:connections")  # Clean up
        except Exception as e:
            logger.error(f"Error decrementing connection count for room {self.room_id}: {e}")
        finally:
            await redis_client.close()

    async def is_duplicate_message(self, message_key):
        try:
            redis_client = redis.Redis(
                host=settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0][0],
                port=settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0][1],
                decode_responses=True
            )
            async with redis_client.pipeline() as pipe:
                pipe.setex(message_key, 60, 1)
                pipe.exists(message_key)
                _, exists = await pipe.execute()
            await redis_client.close()
            return exists > 1
        except Exception as e:
            logger.error(f"Error checking duplicate message {message_key}: {e}")
            return False