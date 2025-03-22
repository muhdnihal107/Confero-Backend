from rest_framework import serializers
from .models import Room,RoomInvite

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
        
class RoomInviteSerializer(serializers.ModelSerializer):
    invitee_id = serializers.IntegerField()
    room_slug = serializers.SlugField()

    class Meta:
        model = RoomInvite
        fields = ['id', 'inviter_id', 'invitee_id', 'room_slug']

    def validate(self, data):
        inviter_id = self.context['request'].user.id
        invitee_id = data.get('invitee_id')
        room_slug = data.get('room_slug')

        # Simple validation: Check if the user is inviting themselves
        if invitee_id == inviter_id:
            raise serializers.ValidationError("You cannot invite yourself.")

        # Check if the room exists
        if not Room.objects.filter(slug=room_slug).exists():
            raise serializers.ValidationError("Room does not exist.")

        return data

    def create(self, validated_data):
        invitee_id = validated_data.pop('invitee_id')
        room_slug = validated_data.pop('room_slug')
        inviter_id = self.context['request'].user.id
        room = Room.objects.get(slug=room_slug)
        room_invite = RoomInvite.objects.create(
            inviter_id=inviter_id,
            invitee_id=invitee_id,
            room=room,
            **validated_data
        )
        return room_invite
        