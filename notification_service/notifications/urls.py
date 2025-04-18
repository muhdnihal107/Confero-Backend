from django.urls import path
from .views import NotificationListView, test_auth, NotificationAllView, ClearNotifications,NotificationReadView,ReadedNotificationListView

urlpatterns = [
    path('all/', NotificationAllView.as_view(), name='notifications'),
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/readed/', ReadedNotificationListView.as_view(), name='notifications'),
    path('test-auth/', test_auth, name='test-auth'),
    path('clear/', ClearNotifications.as_view(), name='clear'),
    path("read/<uuid:id>/", NotificationReadView.as_view(), name="mark-notification-read"),

]
