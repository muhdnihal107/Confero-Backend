from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser, Profile,Friendship,FriendRequest
from .serializers import RegisterSerializer, LoginSerializer, ProfileSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,FriendRequestSerializer, UserSerializer
from rest_framework.permissions import IsAuthenticated,AllowAny
from django.core.mail import send_mail
import uuid
import logging
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from google.oauth2 import id_token 
from google.auth.transport import requests
from django.shortcuts import get_object_or_404
import jwt
from django.conf import settings
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger("django")


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            verification_url = request.build_absolute_uri(
                f"/api/auth/verify-email/{user.verification_token}/"
            )

            send_mail(
                'Verify your email',
                f'Click the link to verify your email: {verification_url}',
                'from@example.com',
                [user.email],
                fail_silently=False,
            )

            return Response(
                {"message": "Registration successful. Please check your email to verify your account."},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# -------------------------------------------------------------------------------------

class UserListView(APIView):
    # permission_classes = [IsAuthenticated]  # Require authentication

    def get(self, request):
        users = CustomUser.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
# -------------------------------------------------------------------------------------

class VerifyEmailView(APIView):
    def get(self, request, token):
        try:
            user = CustomUser.objects.get(verification_token=token)
            if not user.email_verified:
                user.email_verified = True
                user.is_active = True  
                user.save()
                return Response(
                    {"message": "Email verified successfully."},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"message": "Email already verified."}, status=status.HTTP_200_OK
                )
        except CustomUser.DoesNotExist:
            return Response(
                {"message": "Invalid verification token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
# -------------------------------------------------------------------------------------

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = CustomUser.objects.get(email=serializer.validated_data['email'])
            if not user.email_verified:
                return Response({"error": "Email not verified"}, status=status.HTTP_403_FORBIDDEN)
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            custom_payload = {
                'user_id': user.id,
                'email': user.email,
                'username': user.username,
                'exp': refresh.access_token.payload['exp'],  # Copy expiration
                'iat': refresh.access_token.payload['iat'],  # Copy issued at
                'jti': refresh.access_token.payload['jti'],  # Copy token ID
                'token_type': 'access'
            }
            custom_access_token = jwt.encode(custom_payload, settings.SIMPLE_JWT['SIGNING_KEY'], algorithm='HS256')
            return Response({
                "refresh_token": str(refresh),
                "access_token": custom_access_token,
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -------------------------------------------------------------------------------------

# class GoogleAuthView(APIView):
#     @psa('social:complete')
#     def post(self, request, backend):
#         try:
#             user = request.backend.do_auth(request.data.get('code'))  # Use 'code' instead of 'access_token'
#             if user:
#                 refresh = RefreshToken.for_user(user)
#                 return Response({
#                     "access_token": str(refresh.access_token),
#                     "refresh_token": str(refresh),
#                 }, status=status.HTTP_200_OK)
#             return Response({'error': 'Authentication failed'}, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# -------------------------------------------------------------------------------------


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        print('Request FILES:', request.FILES)
        print('Request DATA:', request.data)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#-------------------------------------------------------------------------------------

class ForgotPasswordView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = CustomUser.objects.get(email=email)
            user.reset_token = uuid.uuid4()
            user.reset_token_expiry = timezone.now() + timezone.timedelta(hours=1)  # Token expires in 1 hour
            user.save()

            # Send reset email
            frontend_url = f"http://localhost:5173/reset-password/{user.reset_token}/"
            send_mail(
                'Password Reset Request',
                f'Click the link to reset your password: {frontend_url}',
                'muhdnihal132@gmail.com',
                [user.email],
                fail_silently=False,
            )

            return Response(
                {"message": "Password reset link sent to your email."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#-------------------------------------------------------------------------------------

class ResetPasswordView(APIView):
    def post(self, request, token):  # Accept the `token` argument
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            new_password = serializer.validated_data['new_password']

            try:
                user = CustomUser.objects.get(reset_token=token)
                if user.reset_token_expiry < timezone.now():
                    return Response(
                        {"message": "Reset token has expired."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                user.password = make_password(new_password)
                user.reset_token = None  
                user.reset_token_expiry = None  
                user.save()

                return Response(
                    {"message": "Password reset successfully."},
                    status=status.HTTP_200_OK,
                )
            except CustomUser.DoesNotExist:
                return Response(
                    {"message": "Invalid reset token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ------------------------------------------------------------------------------------------
import logging
import json

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = "1092656538511-9g9vtc7715g4gsm088tjjiac7ksu9ita.apps.googleusercontent.com"

@csrf_exempt
def google_login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            credential = data.get('credential')  

            if not credential:
                logger.error('Missing credential')
                return JsonResponse({'error': 'Missing credential'}, status=400)

            id_info = id_token.verify_oauth2_token(
                credential,
                requests.Request(),
                GOOGLE_CLIENT_ID
            )

            if id_info['aud'] != GOOGLE_CLIENT_ID:
                logger.error(f'Invalid audience: {id_info["aud"]}')
                return JsonResponse({'error': 'Invalid audience'}, status=400)

            email = id_info['email']
            user, created = CustomUser.objects.get_or_create(email=email)
            if created:
                user.username = email
                user.save()

            login(request, user)
            return JsonResponse({'message': 'Google login successful', 'user': {'email': user.email}})
        except ValueError as e:
            logger.error(f'Invalid Google token: {e}')
            return JsonResponse({'error': 'Invalid Google token'}, status=400)
        except json.JSONDecodeError:
            logger.error('Invalid JSON payload')
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

#-----------------------------------------------------------------------------------------------
class FetchAllProflieView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        profiles = Profile.objects.exclude(user=request.user)  # Exclude the current user's profile
        serializer = ProfileSerializer(profiles,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)

#--------------------------------------------------------------------------------

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, id, *args, **kwargs):
        try:

            user = CustomUser.objects.get(id=id)
            serializer = UserSerializer(user)
            return Response(serializer.data,status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


#--------------------------------------------------------------------------------
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
class ValidateTokenView(APIView):
    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)
        jwt_auth = JWTAuthentication()
        try:
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            return Response({"user_id": user.id, "email": user.email},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)  
        
#---------------------------------------------------------------------------------------------------


class FriendRequestView(APIView):
    def post(self, request, *args, **kwargs):
        sender = request.user  # The logged-in user
        receiver_id = request.data.get("receiver_id")
        receiver = get_object_or_404(CustomUser, id=receiver_id)

        if FriendRequest.objects.filter(sender=sender, receiver=receiver).exists():
            return Response({"error": "Friend request already sent."}, status=status.HTTP_400_BAD_REQUEST)

        friend_request = FriendRequest.objects.create(sender=sender, receiver=receiver)

        logger.info("test1")
        self.send_notification(friend_request)

        return Response({"message": "Friend request sent!"}, status=status.HTTP_201_CREATED)

    def send_notification(self, friend_request):
        logger.info("test2")
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
                "receiver_id": str(friend_request.receiver.id),
                "message": f"{friend_request.sender.username} sent you a friend request.",
                "type": "friend_request",
                "friend_request_id": str(friend_request.id),
            }

            channel.basic_publish(
                exchange="",
                routing_key="notification_queue",
                body=json.dumps(notification_data)
            )

            connection.close()
        except Exception as e:
            print(f"Error sending notification: {e}")

    
#-------------------------------------------------------------------------------------------------- 
import os
import pika
class FriendRequestActionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def send_notification(self, receiver_id, sender_id, action):
        message = {
            "receiver_id": receiver_id,
            "message": f"Your friend request was {action}.",
            "type":f"friend_request_{action}"
        }
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
            channel.basic_publish(
                exchange="",
                routing_key="notification_queue",
                body=json.dumps(message)
            )
            connection.close()
        except Exception as e:
            print(f"Failed to send notification: {e}")


    def post(self, request, request_id):
        try:
            friend_request = FriendRequest.objects.get(id=request_id)
            action = request.data.get('action')  
            
            if action == 'accept':
                friend_request.status = 'accepted'
                friend_request.save()
                
                Friendship.objects.create(user=friend_request.sender, friend=friend_request.receiver)
                Friendship.objects.create(user=friend_request.receiver, friend=friend_request.sender)
                
                self.send_notification(friend_request.sender.id, friend_request.receiver.id, "accepted")                 
                
                return Response({"message": "Friend request accepted"}, status=status.HTTP_200_OK)
            
            elif action == 'reject':
                friend_request.status = 'rejected'
                friend_request.save()
                
                self.send_notification(friend_request.sender.id, friend_request.receiver.id, "rejected")
                return Response({"message": "Friend request rejected"}, status=status.HTTP_200_OK)
            
            else:
                return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
        except FriendRequest.DoesNotExist:
            return Response({"error": "Friend request not found"}, status=status.HTTP_404_NOT_FOUND)
        
#-------------------------------------------------------------------------------------------------- 


class FetchFriendsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        friends = Friendship.objects.filter(user=request.user).select_related("friend__profile")
        friend_profiles = [friend.friend.profile for friend in friends if hasattr(friend.friend, "profile")]
        serializer = ProfileSerializer(friend_profiles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

 