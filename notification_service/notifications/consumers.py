# notifications/consumer.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Notification

logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("WebSocket connect attempt: scope=%s", self.scope)
        if self.scope['user'].is_anonymous:
            logger.warning("User is anonymous, closing connection")
            await self.close(code=4403)
        else:
            self.user_id = self.scope['user'].id
            self.group_name = f'notifications_{self.user_id}'
            logger.info("Authenticated user: %s, group_name: %s", self.user_id, self.group_name)
            try:
                await self.channel_layer.group_add(self.group_name, self.channel_name)
                await self.accept()
                logger.info("WebSocket connection accepted for user: %s", self.user_id)
            except Exception as e:
                logger.error("Error in connect: %s", str(e))
                await self.close(code=4500)

    async def disconnect(self, close_code):
        logger.info("WebSocket disconnecting with code: %s", close_code)
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        else:
            logger.warning("No group_name set, skipping group_discard")

    async def receive(self, text_data):
        logger.info("Received WebSocket message: %s", text_data)
        try:
            data = json.loads(text_data)
            action = data.get("action")

            if action == "mark_read":
                await self.mark_notifications_as_read()
            else:
                logger.warning("Unknown action received: %s", action)

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")

    async def send_notification(self, event):
        try:
            notification_data = event["notification"]
            await self.send(text_data=json.dumps(notification_data))
        except Exception as e:
            logger.error("Error sending notification: %s", str(e))
