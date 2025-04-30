# room_service/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'room_service.settings')

app = Celery('room_service')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

