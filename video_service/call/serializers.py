# rooms/serializers.py
from rest_framework import serializers
from .models import Conference, ConferenceMessage

class ConferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conference
        fields = ['id', 'name', 'host', 'participants', 'is_active', 'created_at']
        read_only_fields = ['id', 'cre']

class ConferenceMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConferenceMessage
        fields = ['id', 'conference', 'sender', 'content', 'timestamp']
        read_only_fields = ['id', 'timestamp']