from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('reviews', views.ReviewViewSet, basename='reviews')
router.register('favorites', views.FavoriteViewSet, basename='favorites')

urlpatterns = [
    path('', include(router.urls)),
]
