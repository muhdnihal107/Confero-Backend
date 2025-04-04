from django.urls import path
from .views import NotificationListView, test_auth, NotificationAllView, ClearNotifications

urlpatterns = [
    path('all/', NotificationAllView.as_view(), name='notifications'),
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('test-auth/', test_auth, name='test-auth'),
    path('clear/', ClearNotifications.as_view(), name='clear'),
]
