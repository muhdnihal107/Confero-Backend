from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser,Profile,FriendRequest,Friendship
from django.utils import timezone

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
    class Meta:
        model = FriendRequest
        fields = ['id','sender','receiver', 'receiver_id','status','created_at']
    
    def validate_reciever_id(self,value):
        if not CustomUser.objects.filter(id=value).exists():
            raise serializers.ValidationError("Receiver Does Not Exist")
        if value == self.context['request'].user.id:
            raise serializers.ValidationError("you cannot sent friend request to yourself")
        return value
    
    def create(self,validated_data):
        receiver_id = validated_data.pop('receiver_id')
        receiver = CustomUser.objects.get(id=receiver_id)
        sender = self.context['request'].user
        friend_request = FriendRequest.objects.create(sender=sender,receiver=receiver,**validated_data)
        
        
        