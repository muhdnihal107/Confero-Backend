from django.shortcuts import render,get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Room
from .serializers import RoomSerializer,RoomUpdateSerializer,VideoCallScheduleSerializer
import requests
import logging
import pika
import os
import json

logger = logging.getLogger(__name__)


class RoomView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_email = request.user.email  
        user_id = request.user.id

        rooms = Room.objects.filter(creator_id=user_id) | Room.objects.filter(invited_users__contains=[user_email])
        serializer = RoomSerializer(rooms.distinct(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            if not request.user.is_authenticated:
                logger.error("Unauthenticated user attempted to create room")
                return Response({"error": "User not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

            # Create a mutable copy of request.data
            data = request.data if isinstance(request.data, dict) else dict(request.data)
            data['creator_id'] = request.user.id
            data['creator_email'] = request.user.email

            # Handle participants
            if 'participants' not in data or not isinstance(data.get('participants'), list):
                data['participants'] = [request.user.email]
            elif request.user.email not in data['participants']:
                data['participants'].append(request.user.email)

            # Handle thumbnail (multipart/form-data)
            if 'thumbnail' in request.FILES:
                data['thumbnail'] = request.FILES['thumbnail']
                logger.debug(f"Received thumbnail: {data['thumbnail'].name}, size: {data['thumbnail'].size} bytes")
            else:
                data.pop('thumbnail', None)
                logger.debug("No thumbnail provided")

            # Log the data being serialized
            logger.debug(f"Room creation data: {data}")

            serializer = RoomSerializer(data=data)
            if serializer.is_valid():
                room = serializer.save()
                logger.info(f"Room created successfully: ID={room.id}, Name={room.name}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            logger.error(f"Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.exception(f"Failed to create room: {str(e)}")
            return Response({"error": f"Internal server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#---------------------------------------------------------------------------------------------------------------
class RoomCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data.copy()

        data['creator_id'] = request.user.id
        data['creator_email'] = request.user.email

        serializer = RoomSerializer(data=data)
        if serializer.is_valid():
            room = serializer.save()
            return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#---------------------------------------------------------------------------------------------------------------
class RoomUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, room_id):
        room = get_object_or_404(Room, id=room_id)

        if room.creator_id != request.user.id:
            return Response(
                {"error": "You do not have permission to update this room."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RoomUpdateSerializer(room, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Room updated successfully", "room": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#---------------------------------------------------------------------------------------------
class RoomDetails(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request,room_id):
        room= get_object_or_404(Room,id=room_id)
        serializer = RoomSerializer(room)
        return Response(serializer.data,status=status.HTTP_200_OK) 


#---------------------------------------------------------------------------------------------

class PublicRoomsView(APIView):
    def get(self, request):
        public_rooms = Room.objects.all()
        serializer = RoomSerializer(public_rooms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
#----------------------------------------------------------------------------------------------- 
from .tasks import send_room_invite_email
import logging
from celery.exceptions import OperationalError
logger = logging.getLogger(__name__)

class InviteFriendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(Room, id=room_id)
        sender = request.user

        if room.creator_id != sender.id:
            return Response({"error": "Only the room creator can invite friends"}, 
                          status=status.HTTP_403_FORBIDDEN)

        receiver_id = request.data.get("receiver_id")
        friend_email = request.data.get("email")  # Expect email from frontend

        if not receiver_id or not friend_email:
            return Response({"error": "Both receiver_id and email are required"}, 
                          status=status.HTTP_400_BAD_REQUEST)

        # Check if already invited
        if receiver_id in room.invited_users:
            self.send_notification(room, receiver_id, sender)
            return Response({"error": "Friend already invited to this room"}, 
                          status=status.HTTP_400_BAD_REQUEST)

        # Add friend to invited_users
        room.invited_users.append(receiver_id)
        room.save()

        # Send notification
        self.send_notification(room, receiver_id, sender)
        try:
            send_room_invite_email.delay(
                room_id=room.id,
                receiver_id=receiver_id,
                sender_email=sender.email,
                friend_email=friend_email
            )
            logger.info(f"Queued email task for {friend_email} for room {room.id}-----{sender.email}")
        except OperationalError as e:
            logger.error(f"Failed to queue email task: {str(e)}")
            return Response({"message":"couldnt send email"},status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": f"Invited user {friend_email} to room {room.name}!"}, 
                      status=status.HTTP_200_OK)

    def send_notification(self, room, receiver_id, sender):
        try:
            credentials = pika.PlainCredentials(
                os.getenv('RABBITMQ_USER', 'admin'),
                os.getenv('RABBITMQ_PASS', 'adminpassword')
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=os.getenv('RABBITMQ_HOST', 'rabbitmq'),
                    port=int(os.getenv('RABBITMQ_PORT', 5672)),
                    credentials=credentials
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue="notification_queue", durable=True)

            notification_data = {
                "receiver_id": str(receiver_id),
                "message": f"{sender.email} invited you to join room '{room.name}'.",
                "type": "room_invite",
                "friend_request_id": str(room.id),  # Using this field for room_id
            }

            channel.basic_publish(
                exchange="",
                routing_key="notification_queue",
                body=json.dumps(notification_data),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info(f"Notification sent for user {receiver_id} to join room {room.id}")
            connection.close()

        except Exception as e:
            logger.error(f"Error sending notification: {e}")
#--------------------------------------------------------------------------------------------------
class AcceptRoomInviteView(APIView):
    permission_classes =[IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(Room, id=room_id)
        user = request.user

        if not hasattr(user, 'email') or not user.email:
            logger.error(f"User {user.id} has no email address")
            return Response({"error": "User email not found"}, status=status.HTTP_400_BAD_REQUEST)

        if user.id not in room.invited_users:
            return Response({"error": f"{user.id} were not invited to this room"}, 
                          status=status.HTTP_403_FORBIDDEN)

        if user.email not in room.participants:  # Convert to string for JSONField consistency
            room.participants.append(user.email)
        
        room.invited_users.remove(user.id)
        room.save()

        self.send_acceptance_notification(room, user)

        return Response({"message": f"Joined room {room.name} successfully!"}, 
                      status=status.HTTP_200_OK)
    
    def send_acceptance_notification(self, room, user):
        try:
            credentials = pika.PlainCredentials(
                os.getenv('RABBITMQ_USER', 'admin'),
                os.getenv('RABBITMQ_PASS', 'adminpassword')
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=os.getenv('RABBITMQ_HOST', 'rabbitmq'),
                    port=int(os.getenv('RABBITMQ_PORT', 5672)),
                    credentials=credentials
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue="notification_queue", durable=True)

            notification_data = {
                "receiver_id": str(room.creator_id),  # Notify the creator
                "message": f"{user.email} has joined your room '{room.name}'.",
                "type": "room_invite_accepted",
                "friend_request_id": str(room.id),  # Room ID for reference
            }

            channel.basic_publish(
                exchange="",
                routing_key="notification_queue",
                body=json.dumps(notification_data),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info(f"Notification sent to creator {room.creator_id} for room {room.id}")
            connection.close()

        except Exception as e:
            logger.error(f"Error sending acceptance notification: {e}")


#--------------------------------------------------------------------------------------------------


class JoinPublicRoomView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(Room, id=room_id)
        user = request.user

        if room.visibility != 'public':
            return Response({"error": "This room is private. You need an invitation to join."}, 
                          status=status.HTTP_403_FORBIDDEN)

        if user.email in room.participants:
            return Response({"error": "You are already a participant in this room."}, 
                          status=status.HTTP_400_BAD_REQUEST)

        room.participants.append(user.email)
        room.save()

        self.send_join_notification(room, user)

        return Response({"message": f"Successfully joined public room '{room.name}'!"}, 
                      status=status.HTTP_200_OK)

    def send_join_notification(self, room, user):
        try:
            credentials = pika.PlainCredentials(
                os.getenv('RABBITMQ_USER', 'admin'),
                os.getenv('RABBITMQ_PASS', 'adminpassword')
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=os.getenv('RABBITMQ_HOST', 'rabbitmq'),
                    port=int(os.getenv('RABBITMQ_PORT', 5672)),
                    credentials=credentials
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue="notification_queue", durable=True)

            notification_data = {
                "receiver_id": str(room.creator_id),  # Notify the creator
                "message": f"{user.email} has joined your public room '{room.name}'.",
                "type": "public_room_joined",
                "friend_request_id": str(room.id),  # Room ID for reference
            }

            channel.basic_publish(
                exchange="",
                routing_key="notification_queue",
                body=json.dumps(notification_data),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info(f"Notification sent to creator {room.creator_id} for room {room.id}")
            connection.close()

        except Exception as e:
            logger.error(f"Error sending join notification: {e}")

#-----------------------------------------------------------------------------------------------

class DeleteRoom(APIView):
    permission_classes=[IsAuthenticated]
    def delete(self,request,room_id):
        room=Room.objects.filter(id=room_id)

        room.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


#------------------------------------------------------------------------------------------------------
class HealthCheckView(APIView):
    def get(self, request):
        return Response({"status": "ok"}, status=200)


class DeleteAllRooms(APIView):
    def delete(self,request):
        room= Room.objects.all()
        room.delete()
        return Response({"deleted":"deleted all"},status=status.HTTP_204_NO_CONTENT)

#------------------------------------------------------------------------------------------------------
logger = logging.getLogger(__name__)

class ScheduleVideoCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        participants = request.data.get('participants', [])  # Expect [{"id": int, "email": str}, ...]
        serializer = VideoCallScheduleSerializer(data={
            'room': request.data.get('room_id'),
            'participants': participants,
            'scheduled_time': request.data.get('scheduled_time'),
            'creator_id': request.user.id,
            'creator_email': request.user.email,
        })
        if serializer.is_valid():
            schedule = serializer.save()
            self.send_schedule_notification(schedule, request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_schedule_notification(self, schedule, sender):
        try:
            credentials = pika.PlainCredentials(
                os.getenv('RABBITMQ_USER', 'admin'),
                os.getenv('RABBITMQ_PASS', 'adminpassword')
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=os.getenv('RABBITMQ_HOST', 'rabbitmq'),
                    port=int(os.getenv('RABBITMQ_PORT', 5672)),
                    credentials=credentials
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue="notification_queue", durable=True)

            for participant in schedule.participants:
                notification_data = {
                    "receiver_id": str(participant['id']),
                    "message": f"{sender.email} scheduled a video call in room '{schedule.room.name}' for {schedule.scheduled_time}.",
                    "type": "video_call_schedule",
                    "friend_request_id": str(schedule.id),
                }
                channel.basic_publish(
                    exchange="",
                    routing_key="notification_queue",
                    body=json.dumps(notification_data),
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                logger.info(f"Notification sent to user {participant['id']} for video call schedule {schedule.id}")
            connection.close()
        except Exception as e:
            logger.error(f"Error sending schedule notification: {e}")
        

