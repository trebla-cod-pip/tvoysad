from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('categories', views.CategoryViewSet, basename='api-categories')
router.register('products', views.ProductViewSet, basename='api-products')

urlpatterns = [
    # Template views
    path('', views.home, name='home'),
    path('catalog/', views.catalog, name='catalog'),
    path('catalog/<slug:slug>/', views.catalog, name='catalog_category'),
    path('item/<slug:slug>/', views.item, name='item'),
    path('bag/', views.bag, name='bag'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-success/', views.order_success, name='order_success'),
    path('favorites/', views.favorites, name='favorites'),

    # Cart API
    path('cart/add/', views.cart_add, name='cart_add'),
    path('cart/update/', views.cart_update, name='cart_update'),
    path('cart/remove/', views.cart_remove, name='cart_remove'),

    # REST API
    path('api/', include(router.urls)),
]
