# auth_service/accounts/apps.py
from django.apps import AppConfig
import threading
import os
class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    # def ready(self):
    #     import accounts.signals

    # def ready(self):
    #     """Start RabbitMQ consumer when Django starts."""
    #     if os.environ.get('RUN_MAIN') == 'true':  # Prevent duplicate execution in dev server
            
    #         # ✅ Move import inside ready() after Django setup
    #         from .rabbitmq_consumer import start_rabbitmq_consumer
            
    #         threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()
