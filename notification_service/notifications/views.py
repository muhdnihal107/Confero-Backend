# notification_service/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer
from rest_framework.decorators import api_view,permission_classes
from rest_framework_simplejwt.authentication import JWTAuthentication

class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user_id=request.user.id)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class NotificationAllView(APIView):
    def get(self,request):
        profiles = Notification.objects.all()
        serializer = NotificationSerializer(profiles,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)

# class NotificationListView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         print(f"Headers: {request.headers}")
#         auth = JWTAuthentication()
#         try:
#             header = auth.get_header(request)
#             print(f"Auth Header: {header}")
#             raw_token = auth.get_raw_token(header)
#             print(f"Raw Token: {raw_token}")
#             validated_token = auth.get_validated_token(raw_token)
#             print(f"Validated Token: {validated_token}")
#             user = auth.get_user(validated_token)
#             print(f"User: {user}")
#         except Exception as e:
#             print(f"Auth Error: {str(e)}")
#         notifications = Notification.objects.filter(user_id=request.user.id)
#         serializer = NotificationSerializer(notifications, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_auth(request):
    return Response({"message": f"Authenticated as {request.user.email}"})