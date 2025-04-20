# rooms/models.py
from django.db import models
from django.utils import timezone

class Conference(models.Model):
    name = models.CharField(max_length=255)
    host = models.CharField(max_length=255)  # user_id of host
    participants = models.JSONField(default=list)  # List of user_ids
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} (Host: {self.host})"

class ConferenceMessage(models.Model):
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=255)  # user_id
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Message from {self.sender} in {self.conference.name}"