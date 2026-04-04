from rest_framework import serializers
from .models import Review, Favorite
from catalog.serializers import ProductListSerializer


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'name', 'rating', 'text', 'created_at']
        read_only_fields = ['id', 'created_at']


class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_slug = serializers.SlugRelatedField(
        source='product', slug_field='slug',
        queryset=__import__('catalog').models.Product.objects.all(),
        write_only=True
    )

    class Meta:
        model = Favorite
        fields = ['id', 'product', 'product_slug', 'created_at']
        read_only_fields = ['id', 'created_at']
