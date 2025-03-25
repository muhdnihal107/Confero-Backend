from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser,Profile,FriendRequest,Friendship
from django.utils import timezone
import pika 
import json
from django.conf import settings
#------------------------------------------------------------------------------
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

#----------------------------------------------------------------------------------
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        return {'email': user.email}

#--------------------------------------------------------------------------------
class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', required=False)  # Allow updating username
    email = serializers.EmailField(source='user.email', read_only=True)
    class Meta:
        model = Profile
        fields = ['username','email','phone_number', 'bio', 'profile_photo']
        
        def update(self, instance, validated_data):
            user_data = validated_data.pop('user', {})
            if 'username' in user_data:
                instance.user.username = user_data['username']
                instance.user.save()

            instance.phone_number = validated_data.get('phone_number', instance.phone_number)
            instance.bio = validated_data.get('bio', instance.bio)
            if 'profile_photo' in validated_data:
                instance.profile_photo = validated_data['profile_photo'] 
            instance.save()
            return instance

#--------------------------------------------------------------------------------
     
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user with this email exists.")
        return value

#----------------------------------------------------------------------------------
    
class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True)

    def validate_token(self, value):
        try:
            user = CustomUser.objects.get(reset_token=value)
            if user.reset_token_expiry < timezone.now():
                raise serializers.ValidationError("Reset token has expired.")
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Invalid reset token.")
        return value
    
#----------------------------------------------------------------------------------

class FriendshipSerializer(serializers.ModelSerializer):
    friend = serializers.SlugRelatedField(slug_field='email', queryset=CustomUser.objects.all())

    class Meta:
        model = Friendship
        fields = ['id', 'friend', 'created_at']
        
#---------------------------------------------------------------------------------------------------

class FriendRequestSerializer(serializers.ModelSerializer):
    receiver_id = serializers.IntegerField(write_only=True)  # Input field for receiver's ID

    class Meta:
        model = FriendRequest
        fields = ['id', 'sender', 'receiver', 'receiver_id', 'status', 'created_at']
        read_only_fields = ['sender', 'receiver', 'created_at']  # receiver is read-only in output

    def validate_receiver_id(self, value):
        if not CustomUser.objects.filter(id=value).exists():
            raise serializers.ValidationError("Receiver does not exist")
        if value == self.context['request'].user.id:
            raise serializers.ValidationError("You cannot send a friend request to yourself")
        return value

    def create(self, validated_data):
        receiver_id = validated_data.pop('receiver_id')  # Get receiver_id from input
        receiver = CustomUser.objects.get(id=receiver_id)  # Fetch the receiver object
        sender = self.context['request'].user  # Sender is the authenticated user
        
        # Create the friend request with sender and receiver objects
        friend_request = FriendRequest.objects.create(
            sender=sender,
            receiver=receiver,
            status='pending'  # Default status, no need to pass from validated_data unless overridden
        )
        self.send_notification(sender, receiver, friend_request)
        return friend_request

    def send_notification(self, sender, receiver, friend_request):
        credentials = pika.PlainCredentials(settings.RABBITMQ['USER'], settings.RABBITMQ['PASSWORD'])
        parameters = pika.ConnectionParameters(
            host=settings.RABBITMQ['HOST'],
            port=settings.RABBITMQ['PORT'],
            virtual_host=settings.RABBITMQ['VHOST'],
            credentials=credentials
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        channel.queue_declare(queue='friend_request_notifications', durable=True)

        message = {
            'type': 'friend_request',
            'sender_id': sender.id,
            'sender_email': sender.email,
            'receiver_id': receiver.id,
            'friend_request_id': friend_request.id,
            'created_at': friend_request.created_at.isoformat()
        }

        channel.basic_publish(
            exchange='',
            routing_key='friend_request_notifications',
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        
        