from django.apps import AppConfig
import threading
import os
class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'


    # def ready(self):
    #     """Start RabbitMQ consumer in a separate thread to avoid blocking Django startup."""
    #     from .rabbitmq_consumer import start_notification_consumer
    #     threading.Thread(target=start_notification_consumer, daemon=True).start()


