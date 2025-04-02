from django.db import models
from django.utils.text import slugify

class Room(models.Model):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]

    creator_id = models.IntegerField()  
    creator_email = models.EmailField(blank=True)  
    name = models.CharField(max_length=100,unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    invited_users = models.JSONField(default=list)
    thumbnail = models.ImageField(upload_to='room_thumbnails/',blank=True,null=True)
    participants = models.JSONField(default=list)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session_id = models.CharField(max_length=100, blank=True, null=True)  # For video call session
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            counter = 1
            while Room.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class RoomInvite(models.Model):
    room = models.ForeignKey(Room,on_delete=models.CASCADE)
    inviter_id = models.IntegerField()
    invitee_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    