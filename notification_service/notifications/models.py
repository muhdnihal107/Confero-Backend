# notification_service/models.py
from django.db import models
import uuid
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(db_index=True)  
    friend_requestId = models.IntegerField(null=True,blank=True)
    notification_type = models.CharField(max_length=50)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        channel_layer = get_channel_layer()
        notification_data = {
            "id": str(self.id),
            "message": self.message,
            "notification_type": self.notification_type,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat(),
            "friend_requestId": self.friend_requestId
        }
        
        async_to_sync(channel_layer.group_send)(
            f"notifications_{self.user_id}",
            {"type": "send_notification", "notification": notification_data}
        )

    def __str__(self):
        return f"Notification {self.id} for user {self.user_id}"