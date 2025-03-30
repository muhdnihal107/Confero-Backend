from django.urls import path,include
from .views import NotificationListView,test_auth,NotificationAllView

urlpatterns = [
    path('all/', NotificationAllView.as_view(), name='notifications'),

    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('test-auth/', test_auth, name='test-auth'),
]
