from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser, Profile,Friendship,FriendRequest
from .serializers import RegisterSerializer, LoginSerializer, ProfileSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,FriendRequestSerializer
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
import uuid
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from google.oauth2 import id_token 
from google.auth.transport import requests




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
            return Response({
                "refresh_token": str(refresh),
                "access_token": str(refresh.access_token),
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
    def get(self,request):
        profiles = Profile.objects.all()
        serializer = ProfileSerializer(profiles,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)

#--------------------------------------------------------------------------------
from rest_framework_simplejwt.tokens import AccessToken
from utils.rabbitmq import RabbitMQClient

class ValidateTokenView(APIView):
    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            email = access_token['email']
            # Publish the validation result to RabbitMQ
            rabbitmq_client = RabbitMQClient()
            rabbitmq_client.connect()
            rabbitmq_client.publish_message(
                queue_name='auth_response_queue',
                message={
                    'valid': True,
                    'user_id': user_id,
                    'email': email,
                    'request_id': request.data.get('request_id')
                }
            )
            rabbitmq_client.close()
            return Response({"message": "Token validation request sent"}, status=status.HTTP_200_OK)
        except Exception as e:
            rabbitmq_client = RabbitMQClient()
            rabbitmq_client.connect()
            rabbitmq_client.publish_message(
                queue_name='auth_response_queue',
                message={
                    'valid': False,
                    'error': str(e),
                    'request_id': request.data.get('request_id')
                }
            )
            rabbitmq_client.close()
            return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)  
        
#---------------------------------------------------------------------------------------------------

class FriendRequestView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self,request):
        serializer = FriendRequestSerializer(data=request.data, context={'request':request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Friend request sent"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
#-------------------------------------------------------------------------------------------------- 

class FriendRequestActionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self,request,request_id):
        try:
            friend_request = FriendRequest.objects.get(id=request_id, receiver= request.user)
            action = request.data('action')
            
            if action == 'accept':
                friend_request.status = 'accepted'
                friend_request.save()
                
                Friendship.objects.create(user=friend_request.sender,friend = friend_request.receiver)
                Friendship.objects.create(user=friend_request.receiver,friend= friend_request.sender)
            elif action == 'reject':
                friend_request.status = 'rejected'
                friend_request.save()
                return Response({"message": "Friend request rejected"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
        except FriendRequest.DoesNotExist:
            return Response({"error": "Friend request not found"}, status=status.HTTP_404_NOT_FOUND)