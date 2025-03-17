
from django.urls import path
from .views import RegisterView, LoginView,ProfileView,GoogleAuthView,VerifyEmailView,ForgotPasswordView,ResetPasswordView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('google/', GoogleAuthView.as_view(), name='google_login'),
    path('profile/', ProfileView.as_view(), name='profile'),# Add this
]