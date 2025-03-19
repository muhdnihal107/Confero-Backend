from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Room
from .serializers import RoomSerializer, PublicRoomSerializer
import requests

class RoomView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_email = request.user.email  
        user_id = request.user.id

        rooms = Room.objects.filter(creator_id=user_id) | Room.objects.filter(invited_users__contains=[user_email])
        serializer = RoomSerializer(rooms.distinct(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user_email = request.user.email
        user_id = request.user.id

        serializer = RoomSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creator_id=user_id, creator_email=user_email)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, slug):
        user_id = request.user.id
        try:
            room = Room.objects.get(slug=slug, creator_id=user_id)
            serializer = RoomSerializer(room, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Room.DoesNotExist:
            return Response({"error": "Room not found or you are not the creator"}, status=status.HTTP_404_NOT_FOUND)

class PublicRoomsView(APIView):
    def get(self, request):
        public_rooms = Room.objects.filter(visibility='public')
        serializer = PublicRoomSerializer(public_rooms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
