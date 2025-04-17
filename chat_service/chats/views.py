# chat_service/chats/views.py
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from chats.models import ChatGroup, Message
from chats.serializers import ChatGroupSerializer, MessageSerializer
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import uuid

class ChatGroupListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request):
        queryset = ChatGroup.objects.filter(participants__contains=[request.user.email])
        serializer = ChatGroupSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    def post(self,request):
        serializer = ChatGroupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(participants=serializer.validated_data['participants'])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save(participants=serializer.validated_data['participants'])

class MessageListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Message.objects.filter(chat_group__participants__contains=[request.user.email])
        chat_group_id = request.query_params.get('chat_group')
        if chat_group_id:
            try:
                uuid.UUID(chat_group_id)  # Validate UUID
                queryset = queryset.filter(chat_group_id=chat_group_id)
            except ValueError:
                return Response(
                    {"error": "Invalid chat_group UUID"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        serializer = MessageSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create a new message and broadcast it to the chat group via WebSocket.
        """
        serializer = MessageSerializer(data=request.data)
        if serializer.is_valid():
            try:
                chat_group = ChatGroup.objects.get(id=serializer.validated_data['chat_group'].id)
                if request.user.email not in chat_group.participant_emails:
                    return Response(
                        {"error": "You are not a participant in this chat"},
                        status=status.HTTP_403_FORBIDDEN
                    )
                message = serializer.save(sender_email=request.user.email)
                # Convert UUIDs to strings for WebSocket broadcast
                message_data = MessageSerializer(message).data
                message_data['id'] = str(message_data['id'])
                message_data['chat_group'] = str(message_data['chat_group'])
                # Broadcast to WebSocket group
                channel_layer = get_channel_layer()
                chat_group_id = str(serializer.validated_data['chat_group'].id)
                async_to_sync(channel_layer.group_send)(
                    f"chat_{chat_group_id}",
                    {
                        'type': 'chat_message',
                        'message': message_data
                    }
                )
                return Response(message_data, status=status.HTTP_201_CREATED)
            except ObjectDoesNotExist:
                return Response(
                    {"error": "Chat group does not exist"},
                    status=status.HTTP_404_NOT_FOUND
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)