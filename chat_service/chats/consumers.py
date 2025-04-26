# chat_service/chats/consumers.py
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from chats.models import ChatGroup, Message
import logging

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.chat_group_id = self.scope['url_route']['kwargs']['group_id']
        self.group_name = f"chat_{self.chat_group_id}"
        self.user = self.scope['user']

        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            logger.warning("Unauthenticated user attempted to connect")
            await self.close(code=4001, reason="Invalid or missing token")
            return

        if not await self.is_valid_participant():
            logger.warning(f"{self.user.email} not in chat group {self.chat_group_id}")
            await self.close(code=4003, reason="Not a participant")
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"{self.user.email} connected to {self.group_name}")

        # Mark messages as read upon connection
        updated_message_ids = await self.mark_messages_as_read()
        if updated_message_ids:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'read_receipt',
                    'user_email': self.user.email,
                    'message_ids': updated_message_ids
                }
            )

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"{self.user.email} disconnected from {self.group_name}")

    async def receive_json(self, content):
        message_type = content.get('type')
        if message_type != 'message':
            await self.send_json({'error': 'Invalid message type'})
            return

        text_content = content.get('content', '')
        msg_type = content.get('message_type', 'text')
        if not text_content and msg_type == 'text':
            await self.send_json({'error': 'Text content required for text messages'})
            return

        if msg_type not in ['text']:
            await self.send_json({'error': 'Only text messages supported via WebSocket'})
            return

        try:
            message = await self.save_message(
                sender_email=self.user.email,
                content=text_content,
                message_type=msg_type
            )
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': str(message.id),
                        'sender_email': message.sender_email,
                        'content': message.content,
                        'message_type': message.message_type,
                        'created_at': message.created_at.isoformat(),
                        'chat_group': str(message.chat_group.id),
                        'read_by': message.read_by
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error processing message from {self.user.email}: {e}")
            await self.send_json({'error': str(e)})

    async def chat_message(self, event):
        await self.send_json(event['message'])

    async def read_receipt(self, event):
        await self.send_json({
            'type': 'read_receipt',
            'user_email': event['user_email'],
            'message_ids': event['message_ids']
        })

    @database_sync_to_async
    def is_valid_participant(self):
        try:
            group = ChatGroup.objects.get(id=self.chat_group_id)
            return self.user.email in group.participant_emails
        except ChatGroup.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, sender_email, content, message_type):
        group = ChatGroup.objects.get(id=self.chat_group_id)
        message = Message.objects.create(
            chat_group=group,
            sender_email=sender_email,
            message_type=message_type,
            content=content,
        )
        return message

    @database_sync_to_async
    def mark_messages_as_read(self):
        try:
            group = ChatGroup.objects.get(id=self.chat_group_id)
            messages = Message.objects.filter(
                chat_group=group,
                read_by__not__contains=[self.user.email]
            ).exclude(sender_email=self.user.email)
            updated_message_ids = []
            for message in messages:
                message.read_by.append(self.user.email)
                message.save()
                updated_message_ids.append(str(message.id))
            logger.info(f"{len(updated_message_ids)} messages marked as read by {self.user.email} in chat {self.chat_group_id}")
            return updated_message_ids
        except ChatGroup.DoesNotExist:
            logger.error(f"Chat group {self.chat_group_id} does not exist")
            return []