from rest_framework import serializers
from .models import Room,RoomInvite

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'creator_id', 'creator_email', 'name', 'slug', 'description', 
                 'visibility', 'invited_users', 'thumbnail', 'participants', 
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    # def validate(self, data):
    #     """
    #     Add any custom validation if needed
    #     """
    #     return data
    
class RoomUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["name", "description", "visibility", "invited_users", "thumbnail"]

    def validate_name(self, value):
        room_id = self.instance.id if self.instance else None
        if Room.objects.exclude(id=room_id).filter(name=value).exists():
            raise serializers.ValidationError("A room with this name already exists.")
        return value

class PublicRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'name', 'slug', 'description', 'creator_email', 'thumbnail', 'participants', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']
        
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
        