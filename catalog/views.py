import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Category, Product
from .serializers import (
    CategorySerializer, ProductListSerializer,
    ProductDetailSerializer
)


# ── Cart helpers ──────────────────────────────────────────────────────────────

def get_cart(request):
    return request.session.get('cart', {})


def save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


# ── Template views ─────────────────────────────────────────────────────────────

def home(request):
    from pages.models import SiteSettings
    featured = Product.objects.filter(is_active=True, is_featured=True)[:8]
    categories = Category.objects.filter(is_active=True, parent=None)[:8]
    return render(request, 'catalog/home.html', {
        'featured_products': featured,
        'categories': categories,
        'site_settings': SiteSettings.get(),
    })


def catalog(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True, parent=None)

    category_slug = request.GET.get('category')
    tag = request.GET.get('tag')
    sort = request.GET.get('sort', 'new')
    search = request.GET.get('q', '')

    active_category = None
    if category_slug:
        active_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=active_category)

    if tag:
        products = products.filter(tags__icontains=tag)

    if search:
        from django.db.models.functions import Lower
        from django.db.models import Q
        s = search.lower()
        products = products.annotate(
            name_lower=Lower('name'),
            desc_lower=Lower('description'),
        ).filter(Q(name_lower__contains=s) | Q(desc_lower__contains=s))

    sort_map = {
        'new': '-created_at',
        'price_asc': 'price',
        'price_desc': '-price',
        'name': 'name',
        'rating': '-rating',
    }
    products = products.order_by(sort_map.get(sort, '-created_at'))

    return render(request, 'catalog/catalog.html', {
        'products': products,
        'categories': categories,
        'active_category': active_category,
        'active_tag': tag,
        'sort': sort,
        'search': search,
        'total': products.count(),
    })


def item(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product.id)[:4]
    from reviews.models import Review
    reviews = Review.objects.filter(product=product, is_approved=True).order_by('-created_at')
    return render(request, 'catalog/item.html', {
        'product': product,
        'related_products': related,
        'reviews': reviews,
    })


@ensure_csrf_cookie
def bag(request):
    cart = get_cart(request)
    items = []
    total = 0
    for slug, qty in cart.items():
        try:
            product = Product.objects.get(slug=slug, is_active=True)
            subtotal = product.price * qty
            total += subtotal
            items.append({'product': product, 'qty': qty, 'subtotal': subtotal})
        except Product.DoesNotExist:
            pass
    return render(request, 'catalog/bag.html', {
        'items': items,
        'total': total,
        'count': sum(cart.values()),
    })


def checkout(request):
    cart = get_cart(request)
    if not cart:
        return redirect('bag')
    items = []
    total = 0
    for slug, qty in cart.items():
        try:
            product = Product.objects.get(slug=slug, is_active=True)
            subtotal = product.price * qty
            total += subtotal
            items.append({'product': product, 'qty': qty, 'subtotal': subtotal})
        except Product.DoesNotExist:
            pass

    if request.method == 'POST':
        from orders.models import Order, OrderItem
        order = Order.objects.create(
            name=request.POST.get('name', ''),
            phone=request.POST.get('phone', ''),
            email=request.POST.get('email', ''),
            delivery_address=request.POST.get('delivery_address', ''),
            delivery_date=request.POST.get('delivery_date') or None,
            delivery_time=request.POST.get('delivery_time', ''),
            comment=request.POST.get('comment', ''),
            payment_method=request.POST.get('payment_method', 'card'),
            total_amount=total,
        )
        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['qty'],
                price=item['product'].price,
            )
        save_cart(request, {})
        return redirect('order_success')

    return render(request, 'catalog/checkout.html', {
        'items': items,
        'total': total,
    })


def order_success(request):
    return render(request, 'catalog/order_success.html')


def favorites(request):
    from reviews.models import Favorite
    session_id = request.session.session_key or ''
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
    favs = Favorite.objects.filter(session_id=session_id).select_related('product')
    products = [f.product for f in favs if f.product.is_active]
    return render(request, 'catalog/favorites.html', {'products': products})


# ── Cart API ────────────────────────────────────────────────────────────────────

@require_POST
def cart_add(request):
    data = json.loads(request.body)
    slug = data.get('slug')
    qty = int(data.get('qty', 1))
    cart = get_cart(request)
    cart[slug] = cart.get(slug, 0) + qty
    save_cart(request, cart)
    return JsonResponse({'count': sum(cart.values()), 'cart': cart})


@require_POST
def cart_update(request):
    data = json.loads(request.body)
    slug = data.get('slug')
    qty = int(data.get('qty', 1))
    cart = get_cart(request)
    if qty <= 0:
        cart.pop(slug, None)
    else:
        cart[slug] = qty
    save_cart(request, cart)
    total = sum(
        Product.objects.get(slug=s).price * q
        for s, q in cart.items()
        if Product.objects.filter(slug=s).exists()
    )
    return JsonResponse({'count': sum(cart.values()), 'cart': cart, 'total': str(total)})


@require_POST
def cart_remove(request):
    data = json.loads(request.body)
    slug = data.get('slug')
    cart = get_cart(request)
    cart.pop(slug, None)
    save_cart(request, cart)
    return JsonResponse({'count': sum(cart.values()), 'cart': cart})


# ── DRF ViewSets ──────────────────────────────────────────────────────────────

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    lookup_field = 'slug'


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductListSerializer
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'rating', 'created_at', 'name']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        tag = self.request.query_params.get('tag')
        featured = self.request.query_params.get('featured')
        if category:
            qs = qs.filter(category__slug=category)
        if tag:
            qs = qs.filter(tags__icontains=tag)
        if featured:
            qs = qs.filter(is_featured=True)
        return qs

    @action(detail=False, methods=['get'])
    def featured(self, request):
        products = self.get_queryset().filter(is_featured=True)[:8]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def fresh(self, request):
        products = self.get_queryset().order_by('-created_at')[:8]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)
