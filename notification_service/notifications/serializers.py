from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['user_id','friend_requestId', 'notification_type', 'message', 'is_read', 'created_at']