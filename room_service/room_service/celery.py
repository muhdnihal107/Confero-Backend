# room_service/celery.py
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'room_service.settings')

app = Celery('room_service')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send-scheduled-call-notifications-every-minute': {
        'task': 'rooms.tasks.send_scheduled_call_notifications',
        'schedule': crontab(minute='*'),  # Run every minute
    },
}
