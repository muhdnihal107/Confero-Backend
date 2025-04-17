# chat_service/chats/serializers.py
from rest_framework import serializers
from chats.models import ChatGroup, Message
from django.core.validators import FileExtensionValidator

class ChatGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatGroup
        fields = ['id', 'name', 'is_group_chat', 'participants', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_participants(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("Participants must be a non-empty list of emails")
        return value

class MessageSerializer(serializers.ModelSerializer):
    media_file = serializers.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov'])]
    )

    class Meta:
        model = Message
        fields = ['id', 'chat_group', 'sender_email', 'message_type', 'content', 'media_file', 'created_at', 'read_by']
        read_only_fields = ['id', 'sender_email', 'created_at', 'read_by']

    def validate(self, attrs):
        message_type = attrs.get('message_type', 'text')
        content = attrs.get('content')
        media_file = attrs.get('media_file')

        if message_type == 'text' and not content:
            raise serializers.ValidationError("Text content required for text messages")
        if message_type in ['image', 'video'] and not media_file:
            raise serializers.ValidationError(f"{message_type.capitalize()} file required for {message_type} messages")
        if message_type in ['image', 'video'] and content:
            raise serializers.ValidationError(f"Content not allowed for {message_type} messages")
        return attrs