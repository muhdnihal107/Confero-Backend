from django.shortcuts import render,get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Room
from .serializers import RoomSerializer,RoomUpdateSerializer
import requests
import logging

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
            
            serializer = RoomSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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



class PublicRoomsView(APIView):
    def get(self, request):
        public_rooms = Room.objects.all()
        serializer = RoomSerializer(public_rooms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class DeleteRoom(APIView):
    def delete(self,request):
        id = request.data["id"]
        room=Room.objects.filter(id=id)

        room.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class HealthCheckView(APIView):
    def get(self, request):
        return Response({"status": "ok"}, status=200)


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
        

