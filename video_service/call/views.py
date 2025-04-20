# rooms/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Conference, ConferenceMessage
from .serializers import ConferenceSerializer, ConferenceMessageSerializer

class ConferenceCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        serializer = ConferenceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(host=str(request.user.id))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ConferenceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, format=None):
        try:
            conference = Conference.objects.get(id=id)
            serializer = ConferenceSerializer(conference)
            return Response(serializer.data)
        except Conference.DoesNotExist:
            return Response(
                {"detail": "Conference not found."},
                status=status.HTTP_404_NOT_FOUND
            )

class ConferenceEndView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id, format=None):
        try:
            conference = Conference.objects.get(id=id)
            if str(request.user.id) != conference.host:
                return Response(
                    {"detail": "Only the host can end the conference."},
                    status=status.HTTP_403_FORBIDDEN
                )
            conference.is_active = False
            conference.save()
            return Response({"status": "Conference ended"})
        except Conference.DoesNotExist:
            return Response(
                {"detail": "Conference not found."},
                status=status.HTTP_404_NOT_FOUND
            )

class ConferenceMessageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conference_id, format=None):
        messages = ConferenceMessage.objects.filter(
            conference__id=conference_id
        ).order_by('timestamp')
        serializer = ConferenceMessageSerializer(messages, many=True)
        return Response(serializer.data)