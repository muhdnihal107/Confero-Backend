
from django.urls import path
from .views import RegisterView, LoginView,ProfileView,VerifyEmailView,ForgotPasswordView,ResetPasswordView,google_login,FetchAllProflieView,ValidateTokenView,FriendRequestView,FriendRequestActionView, UserListView,UserDetailView,FetchFriendsView

urlpatterns = [
    path('users/', UserListView.as_view(), name='register'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('verify-email/<uuid:token>/', VerifyEmailView.as_view(), name='verify-email'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/<uuid:token>', ResetPasswordView.as_view(), name='reset-password'),
   # path('google/', GoogleAuthView.as_view(), name='google_login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('google/', google_login, name='google-login'),
    path('profilelist/',FetchAllProflieView.as_view(),name='profile-list'),
    path('validate-token/', ValidateTokenView.as_view(), name='validate-token'),
    path('friend-request/', FriendRequestView.as_view(), name='friend-request'),
    path('friend-request/<int:request_id>/action/', FriendRequestActionView.as_view(), name='friend-request-action'),
    path("user-details/<int:id>/",UserDetailView.as_view(), name="user-detail"),
    path("fetch-friends/",FetchFriendsView.as_view(), name="fetch-friend"),

]