from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser,Profile
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.utils.encoding import force_bytes,force_str
from .utils import email_verification_token,password_reset_token


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = CustomUser
        fields = [ 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        return {'email': user.email}
    
class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', required=False)  # Allow updating username
    email = serializers.EmailField(source='user.email', read_only=True)
    class Meta:
        model = Profile
        fields = ['username','email','phone_number', 'bio', 'profile_photo']
        
        def update(self, instance, validated_data):
        # Update user-related fields (username)
            user_data = validated_data.pop('user', {})
            if 'username' in user_data:
                instance.user.username = user_data['username']
                instance.user.save()

            # Update profile fields
            instance.Phone_number = validated_data.get('Phone_number', instance.Phone_number)
            instance.bio = validated_data.get('bio', instance.bio)
            if 'Profile_photo' in validated_data:
                instance.Profile_photo = validated_data['Profile_photo'] 
            instance.save()
            return instance
        
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user with this email exists.")
        return value
    
class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=6)
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, data):
        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            raise serializers.ValidationError("Invalid reset link")
        if not password_reset_token.check_token(user, data['token']):
            raise serializers.ValidationError("Invalid or expired token")
        return data

    def save(self):
        uid = force_str(urlsafe_base64_decode(self.validated_data['uid']))
        user = CustomUser.objects.get(pk=uid)
        user.set_password(self.validated_data['password'])
        user.save()
        return user