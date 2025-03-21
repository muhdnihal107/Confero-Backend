# notification_service/notifications/consumers.py

from channels.generic.websocket import AsyncWebsocketConsumer
import json

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Add the client to a group based on their user ID (for now, use a test group)
        self.user = self.scope['user']  # Get the authenticated user (if any)
        self.group_name = 'test_notifications'  # Temporary group for testing

        # Add the client to the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        await self.send(text_data=json.dumps({
            'message': 'Connected to notification service'
        }))

    async def disconnect(self, close_code):
        # Remove the client from the group on disconnect
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Handle messages received from the client (for testing)
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '')

        # Echo the message back to the client
        await self.send(text_data=json.dumps({
            'message': f'Echo: {message}'
        }))

    async def send_notification(self, event):
        # Handle notifications sent to the group
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))