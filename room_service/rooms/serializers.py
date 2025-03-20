from rest_framework import serializers
from .models import Room

class RoomSerializer(serializers.ModelSerializer):
    invited_users = serializers.ListField(child=serializers.EmailField(), required=False)
    thumbnail = serializers.ImageField(required=False)
    class Meta:
        model = Room
        fields = ['id', 'name', 'slug', 'description', 'visibility', 'creator_id', 'creator_email', 'invited_users', 'thumbnail', 'participants', 'created_at', 'updated_at']
        read_only_fields = ['slug', 'creator_id', 'creator_email', 'created_at', 'updated_at']

class PublicRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'name', 'slug', 'description', 'creator_email', 'thumbnail', 'participants', 'created_at']
        read_only_fields = ['id', 'slug', 'creator_email', 'created_at']