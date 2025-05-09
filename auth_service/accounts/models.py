from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid


class CustomUserManager(BaseUserManager):
    """Manager for CustomUser model"""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)  # Add this
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)  
    is_active = models.BooleanField(default=True)
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False)  
    email_verified = models.BooleanField(default=False)  
    reset_token = models.UUIDField(null=True, blank=True, editable=False)  
    reset_token_expiry = models.DateTimeField(null=True, blank=True)  
    USERNAME_FIELD = 'email'  
    REQUIRED_FIELDS = ['username']

    objects = CustomUserManager()

    def __str__(self):
        return self.email
    
    
class Profile(models.Model):
    user=models.OneToOneField(CustomUser, on_delete=models.CASCADE,related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Friendship(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='friendships')
    friend = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='friends')
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        unique_together = ('user', 'friend')

    def __str__(self):
        return f"{self.user.username} -> {self.friend.username}"
    

class FriendRequest(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_request')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='receiver_request')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('pending','Pending'),('accepted','Accepted'),('rejected','Rejected')], default='pending')
    
    
    class Meta:
        unique_together = ('sender','receiver')