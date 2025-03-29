# notification_service/models.py
from django.db import models
import uuid

class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField()  # Store CustomUser ID from auth_service
    friend_requestId = models.IntegerField(null=True,blank=True)
    notification_type = models.CharField(max_length=50)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification {self.id} for user {self.user_id}"