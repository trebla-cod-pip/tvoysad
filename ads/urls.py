from django.urls import path
from . import views

urlpatterns = [
    path('go/<str:code>/', views.track_redirect, name='ad_track'),
]
