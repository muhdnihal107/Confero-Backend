from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser, Profile
from .serializers import RegisterSerializer, LoginSerializer, ProfileSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
from social_django.utils import psa
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.urls import reverse
import uuid
from django.contrib.auth.hashers import make_password
from django.utils import timezone



class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Generate verification URL
            verification_url = request.build_absolute_uri(
                f"/api/auth/verify-email/{user.verification_token}/"
            )

            # Send verification email
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
                user.is_active = True  # Activate the user
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

class GoogleAuthView(APIView):
    @psa('social:complete')
    def post(self, request, backend):
        try:
            user = request.backend.do_auth(request.data.get('code'))  # Use 'code' instead of 'access_token'
            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                }, status=status.HTTP_200_OK)
            return Response({'error': 'Authentication failed'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
                user.reset_token = None  # Clear the reset token
                user.reset_token_expiry = None  # Clear the expiry time
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

           