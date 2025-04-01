from django.urls import path
from .views import RoomView, PublicRoomsView,RoomUpdateAPIView

urlpatterns = [
    path('rooms/', RoomView.as_view(), name='rooms'),
    path('rooms/<slug:slug>/', RoomView.as_view(), name='room-detail'),
    path('public-rooms/', PublicRoomsView.as_view(), name='public-rooms'),
    path('update-room/<int:room_id>',RoomUpdateAPIView.as_view(),name='update-room')
]