import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Review, Favorite
from .serializers import ReviewSerializer, FavoriteSerializer
from catalog.models import Product


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    http_method_names = ['get', 'post']

    def get_queryset(self):
        qs = Review.objects.filter(is_approved=True)
        product_slug = self.request.query_params.get('product')
        if product_slug:
            qs = qs.filter(product__slug=product_slug)
        return qs

    def perform_create(self, serializer):
        product_slug = self.request.data.get('product_slug')
        product = Product.objects.get(slug=product_slug)
        serializer.save(product=product)


class FavoriteViewSet(viewsets.ViewSet):
    def _get_session_id(self, request):
        if not request.session.session_key:
            request.session.create()
        return request.session.session_key

    @action(detail=False, methods=['get'])
    def my(self, request):
        session_id = self._get_session_id(request)
        favs = Favorite.objects.filter(session_id=session_id).select_related('product')
        serializer = FavoriteSerializer(favs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add(self, request):
        session_id = self._get_session_id(request)
        slug = request.data.get('slug')
        product = Product.objects.get(slug=slug)
        fav, created = Favorite.objects.get_or_create(product=product, session_id=session_id)
        return Response({'added': created, 'id': fav.id})

    @action(detail=False, methods=['post'])
    def remove(self, request):
        session_id = self._get_session_id(request)
        slug = request.data.get('slug')
        Favorite.objects.filter(product__slug=slug, session_id=session_id).delete()
        return Response({'removed': True})
