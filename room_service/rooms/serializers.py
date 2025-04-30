from rest_framework import serializers
from .models import Room,VideoCallSchedule
import mimetypes
from django.utils import timezone


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'creator_id', 'creator_email', 'name', 'slug', 'description', 
                 'visibility', 'invited_users', 'thumbnail', 'participants','is_live', 
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
    def validate(self, value):
        if Room.objects.filter(name=value).exists():
            raise serializers.ValidationError("A room with this name already exists.")
        return value
    
class RoomUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["name", "description", "visibility", "invited_users", "thumbnail"]

    def validate_name(self, value):
        room_id = self.instance.id if self.instance else None
        if Room.objects.exclude(id=room_id).filter(name=value).exists():
            raise serializers.ValidationError("A room with this name already exists.")
        return value


class VideoCallScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoCallSchedule
        fields = ['id', 'room', 'creator_id', 'creator_email', 'participants', 'scheduled_time', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_scheduled_time(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future.")
        return value

    def validate_participants(self, value):
        if not value:
            raise serializers.ValidationError("At least one participant is required.")
        for p in value:
            if not isinstance(p, dict) or 'id' not in p or 'email' not in p:
                raise serializers.ValidationError("Each participant must have an 'id' and 'email'.")
        return value


        
# class RoomInviteSerializer(serializers.ModelSerializer):
#     invitee_id = serializers.IntegerField()
#     room_slug = serializers.SlugField()

#     class Meta:
#         model = RoomInvite
#         fields = ['id', 'inviter_id', 'invitee_id', 'room_slug']

#     def validate(self, data):
#         inviter_id = self.context['request'].user.id
#         invitee_id = data.get('invitee_id')
#         room_slug = data.get('room_slug')

#         # Simple validation: Check if the user is inviting themselves
#         if invitee_id == inviter_id:
#             raise serializers.ValidationError("You cannot invite yourself.")

#         # Check if the room exists
#         if not Room.objects.filter(slug=room_slug).exists():
#             raise serializers.ValidationError("Room does not exist.")

#         return data

#     def create(self, validated_data):
#         invitee_id = validated_data.pop('invitee_id')
#         room_slug = validated_data.pop('room_slug')
#         inviter_id = self.context['request'].user.id
#         room = Room.objects.get(slug=room_slug)
#         room_invite = RoomInvite.objects.create(
#             inviter_id=inviter_id,
#             invitee_id=invitee_id,
#             room=room,
#             **validated_data
#         )
#         return room_invite
        