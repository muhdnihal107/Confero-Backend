from django.shortcuts import render,get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Room
from .serializers import RoomSerializer,RoomUpdateSerializer
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
                return Response({"error": "User not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
            

            data = request.data.copy()
            data['creator_id'] = request.user.id
            data['creator_email'] = request.user.email

            # Initialize participants and add creator
            if 'participants' not in data or not isinstance(data['participants'], list):
                data['participants'] = [request.user.email]
            elif request.user.email not in data['participants']:
                data['participants'].append(request.user.email)
            
            serializer = RoomSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

import logging

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
            return Response({"error": "Friend already invited to this room"}, 
                          status=status.HTTP_400_BAD_REQUEST)

        # Add friend to invited_users
        room.invited_users.append(receiver_id)
        room.save()

        # Send notification
        self.send_notification(room, receiver_id, sender)

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
    def delete(self,request):
        id = request.data["id"]
        room=Room.objects.filter(id=id)

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


# from utils.rabbitmq import RabbitMQClient

# class JoinRoomView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, slug):
#         user_email = request.user.email
#         try:
#             room = Room.objects.get(slug=slug)
#             if room.visibility == 'public' or user_email in room.invited_users or user_email == room.creator_email:
#                 if user_email not in room.participants:
#                     room.participants.append(user_email)
#                     room.save()

#                     # Publish a message to RabbitMQ
#                     rabbitmq_client = RabbitMQClient()
#                     rabbitmq_client.connect()
#                     rabbitmq_client.publish_message(
#                         queue_name='room_events',
#                         message={
#                             'event': 'user_joined',
#                             'room_id': room.id,
#                             'room_name': room.name,
#                             'user_email': user_email
#                         }
#                     )
#                     rabbitmq_client.close()

#                 return Response({"message": "Joined room successfully"}, status=status.HTTP_200_OK)
#             return Response({"error": "You are not authorized to join this room"}, status=status.HTTP_403_FORBIDDEN)
#         except Room.DoesNotExist:
#             return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)
        

