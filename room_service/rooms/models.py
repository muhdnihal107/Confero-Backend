from django.db import models, transaction
from django.utils.text import slugify
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

class Room(models.Model):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]

    creator_id = models.IntegerField()  
    creator_email = models.EmailField()  # Required
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    invited_users = models.JSONField(default=list)
    thumbnail = models.ImageField(upload_to='room_thumbnails/', blank=True, null=True)
    participants = models.JSONField(default=list)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session_id = models.CharField(max_length=100, blank=True, null=True)  # Clarify purpose later

    def add_participant(self, user_email):
        validate_email(user_email)
        with transaction.atomic():
            room = Room.objects.select_for_update().get(id=self.id)
            if user_email not in room.participants:
                room.participants.append(user_email)
                room.save()
            self.participants = room.participants

    def remove_participant(self, user_email):
        """Remove a participant atomically."""
        with transaction.atomic():
            room = Room.objects.select_for_update().get(id=self.id)
            if user_email in room.participants:
                room.participants.remove(user_email)
                room.save()
            self.participants = room.participants

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            counter = 1
            while Room.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def clean(self):
        if not self.name.strip() or any(c in self.name for c in '#%&'):
            raise ValidationError("Room name must not be empty or contain #, %, or &.")

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['creator_id']),
            models.Index(fields=['name']),
        ]
    
class RoomInvite(models.Model):
    room = models.ForeignKey(Room,on_delete=models.CASCADE)
    inviter_id = models.IntegerField()
    invitee_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    