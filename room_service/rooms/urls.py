from django.urls import path
from .views import RoomView, PublicRoomsView,RoomUpdateAPIView,DeleteRoom,HealthCheckView,InviteFriendView,AcceptRoomInviteView,JoinPublicRoomView,RoomDetails,DeleteAllRooms

urlpatterns = [
    path('rooms/', RoomView.as_view(), name='rooms'),
    path('rooms/<slug:slug>/', RoomView.as_view(), name='room-detail'),
    path('public-rooms/', PublicRoomsView.as_view(), name='public-rooms'),
    path('update-room/<int:room_id>',RoomUpdateAPIView.as_view(),name='update-room'),
    path('delete-room/',DeleteRoom.as_view(),name='delete-room'),
    path('health/', HealthCheckView.as_view(), name='health'),
    path('rooms/<int:room_id>/invite/', InviteFriendView.as_view(), name='invite-friend'),
    path('rooms/<int:room_id>/accept/', AcceptRoomInviteView.as_view(), name='accept-invite'),
    path('rooms/<int:room_id>/join/', JoinPublicRoomView.as_view(), name='join-public-room'),
    path('room/<int:room_id>/',RoomDetails.as_view(),name='room-detail-view'),
    path('deleteall/',DeleteAllRooms.as_view()),
]