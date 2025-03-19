from django.urls import path
from .views import RoomView, PublicRoomsView

urlpatterns = [
    path('rooms/', RoomView.as_view(), name='rooms'),
    path('rooms/<slug:slug>/', RoomView.as_view(), name='room-detail'),
    path('public-rooms/', PublicRoomsView.as_view(), name='public-rooms'),
]