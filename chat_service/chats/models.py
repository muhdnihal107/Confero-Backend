# chat_service/chats/models.py
from django.db import models
from django.core.validators import FileExtensionValidator
import uuid

class ChatGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, blank=True) 
    is_group_chat = models.BooleanField(default=False)
    participants = models.JSONField()  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['participants']),
        ]

    def __str__(self):
        return self.name or f"Chat {self.id} ({'Group' if self.is_group_chat else '1:1'})"

    @property
    def participant_emails(self):
        return self.participants

class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat_group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name='messages')
    sender_email = models.EmailField()  # Stores sender's email
    message_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text'),
            ('image', 'Image'),
            ('video', 'Video'),
        ],
        default='text',
    )
    content = models.TextField(blank=True)  # For text messages
    media_file = models.FileField(
        upload_to='chat_media/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov']
            )
        ],
        max_length=255
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False,blank=True,null=True)
    read_by = models.JSONField(default=list)  

    class Meta:
        indexes = [
            models.Index(fields=['chat_group', 'created_at']),
            models.Index(fields=['sender_email']),
        ]
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender_email} in {self.chat_group.id}: {self.message_type}"
