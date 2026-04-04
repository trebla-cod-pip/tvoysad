from django.urls import path
from . import views

urlpatterns = [
    path('contacts/', views.contact_page, name='contacts'),
    path('contacts/submit/', views.contact_submit, name='contact_submit'),
    path('delivery/', views.delivery_page, name='delivery'),
    path('page/<slug:slug>/', views.page_detail, name='page_detail'),
]
