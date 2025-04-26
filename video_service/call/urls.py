# rooms/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('conferences/', views.ConferenceCreateView.as_view(), name='conference-create'),
    path('conferences/<str:id>/', views.ConferenceDetailView.as_view(), name='conference-detail'),
    path('conferences/<str:id>/end/', views.ConferenceEndView.as_view(), name='conference-end'),
    path('conferences/<str:id>/join/', views.ConferenceJoinView.as_view(), name='conference-join'),
    path('conferences/<str:conference_id>/messages/', views.ConferenceMessageListView.as_view(), name='conference-messages'),
]