from django.urls import path
from . import views

urlpatterns = [
    path('tg/init/', views.tg_init, name='tg_init'),
    path('tg/send/', views.tg_send_message, name='tg_send_message'),
]
