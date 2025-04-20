# rooms/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conference, ConferenceMessage

class VideoCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conference_id = self.scope['url_route']['kwargs']['conference_id']
        self.conference_group_name = f'video_{self.conference_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Join conference group
        await self.channel_layer.group_add(
            self.conference_group_name,
            self.channel_name
        )

        await self.accept()

        # Add user to conference participants
        await self.add_user_to_conference()

        # Notify others about new participant
        await self.channel_layer.group_send(
            self.conference_group_name,
            {
                'type': 'user_joined',
                'user_id': str(self.user.id),
                'username': self.user.username,
            }
        )

    async def disconnect(self, close_code):
        # Remove user from conference participants
        await self.remove_user_from_conference()

        # Notify others about participant leaving
        await self.channel_layer.group_send(
            self.conference_group_name,
            {
                'type': 'user_left',
                'user_id': str(self.user.id),
                'username': self.user.username,
            }
        )

        # Leave conference group
        await self.channel_layer.group_discard(
            self.conference_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'offer':
            # Forward WebRTC offer to other participants
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_offer',
                    'sender': str(self.user.id),
                    'offer': data['offer'],
                    'to': data.get('to'),  # Specific user or None for all
                }
            )
        elif message_type == 'answer':
            # Forward WebRTC answer to other participants
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_answer',
                    'sender': str(self.user.id),
                    'answer': data['answer'],
                    'to': data.get('to'),
                }
            )
        elif message_type == 'ice_candidate':
            # Forward ICE candidate to other participants
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'ice_candidate',
                    'sender': str(self.user.id),
                    'candidate': data['candidate'],
                    'to': data.get('to'),
                }
            )
        elif message_type == 'chat_message':
            # Save chat message and broadcast
            message = await self.save_chat_message(data['message'])
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'sender': str(self.user.id),
                    'username': self.user.username,
                    'message': message.content,
                    'timestamp': str(message.timestamp),
                }
            )

    # Handler methods for different message types
    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user_id': event['user_id'],
            'username': event['username'],
        }))

    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user_id': event['user_id'],
            'username': event['username'],
        }))

    async def webrtc_offer(self, event):
        # Only send to the specified user or everyone except sender
        if not event.get('to') or event['to'] == str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'offer',
                'sender': event['sender'],
                'offer': event['offer'],
            }))

    async def webrtc_answer(self, event):
        if not event.get('to') or event['to'] == str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'answer',
                'sender': event['sender'],
                'answer': event['answer'],
            }))

    async def ice_candidate(self, event):
        if not event.get('to') or event['to'] == str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'ice_candidate',
                'sender': event['sender'],
                'candidate': event['candidate'],
            }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'sender': event['sender'],
            'username': event['username'],
            'message': event['message'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def add_user_to_conference(self):
        conference = Conference.objects.get(id=self.conference_id)
        if str(self.user.id) not in conference.participants:
            conference.participants.append(str(self.user.id))
            conference.save()

    @database_sync_to_async
    def remove_user_from_conference(self):
        conference = Conference.objects.get(id=self.conference_id)
        if str(self.user.id) in conference.participants:
            conference.participants.remove(str(self.user.id))
            conference.save()

    @database_sync_to_async
    def save_chat_message(self, message):
        conference = Conference.objects.get(id=self.conference_id)
        return ConferenceMessage.objects.create(
            conference=conference,
            sender=str(self.user.id),
            content=message
        )