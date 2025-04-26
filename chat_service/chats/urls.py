# chat_service/chats/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from chats.views import ChatGroupListCreateView, MessageListCreateView,MarkMessagesReadView,ChatGroupUpdateView



urlpatterns = [
    path('groups/', ChatGroupListCreateView.as_view(), name='chat-group-list-create'),
    path('messages/', MessageListCreateView.as_view(), name='message-list-create'),
    path('messages/mark-read/', MarkMessagesReadView.as_view(), name='mark-messages-read'),
    path('groups/<uuid:group_id>/', ChatGroupUpdateView.as_view(), name='chat-group-update'),

]