import json

from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Product, ProductAgeVariant
from .serializers import CategorySerializer, ProductDetailSerializer, ProductListSerializer


def get_cart(request):
    return request.session.get('cart', {})


def save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


def parse_cart_key(key):
    """Returns (slug, age_years_or_None). Key format: 'slug' or 'slug|3'."""
    if '|' in key:
        slug, age = key.rsplit('|', 1)
        return slug, int(age)
    return key, None


def build_cart_items(cart):
    parsed = {key: parse_cart_key(key) for key in cart}
    slugs = list({slug for slug, _ in parsed.values()})
    products = {
        p.slug: p
        for p in Product.objects.filter(slug__in=slugs, is_active=True).select_related('category')
    }

    age_variant_keys = {(slug, age) for _, (slug, age) in parsed.items() if age is not None}
    age_variants = {}
    if age_variant_keys:
        qs = ProductAgeVariant.objects.filter(
            product__slug__in=[s for s, _ in age_variant_keys],
        ).select_related('product')
        for v in qs:
            age_variants[(v.product.slug, v.age_years)] = v

    items = []
    total = 0
    count = 0

    for cart_key, qty in cart.items():
        slug, age_years = parsed[cart_key]
        product = products.get(slug)
        if not product:
            continue

        if age_years is not None:
            variant = age_variants.get((slug, age_years))
            price = variant.price if variant else product.price
            age_label = variant.age_label if variant else f'{age_years} лет'
        else:
            price = product.price
            age_label = None

        subtotal = price * qty
        total += subtotal
        count += qty
        items.append({
            'product': product,
            'qty': qty,
            'subtotal': subtotal,
            'price': price,
            'age_years': age_years,
            'age_label': age_label,
            'cart_key': cart_key,
        })

    return items, total, count


def home(request):
    from pages.models import SiteSettings

    featured = Product.objects.filter(
        is_active=True,
        is_featured=True,
    ).select_related('category')[:8]
    categories = Category.objects.filter(
        is_active=True,
        parent=None,
    ).annotate(products_count=Count('products', filter=Q(products__is_active=True))).order_by('sort_order', 'name')[:8]

    return render(
        request,
        'catalog/home.html',
        {
            'featured_products': featured,
            'categories': categories,
            'site_settings': SiteSettings.get(),
        },
    )


def catalog(request):
    products = Product.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.filter(
        is_active=True,
        parent=None,
    ).annotate(products_count=Count('products', filter=Q(products__is_active=True))).order_by('sort_order', 'name')

    category_slug = request.GET.get('category')
    tag = request.GET.get('tag')
    sort = request.GET.get('sort', 'new')
    search = request.GET.get('q', '')

    active_category = None
    if category_slug:
        active_category = get_object_or_404(categories, slug=category_slug)
        products = products.filter(category=active_category)

    if tag:
        products = products.filter(tags__icontains=tag)

    if search:
        from django.db.models.functions import Lower

        search_value = search.lower()
        products = products.annotate(
            name_lower=Lower('name'),
            desc_lower=Lower('description'),
        ).filter(Q(name_lower__contains=search_value) | Q(desc_lower__contains=search_value))

    sort_map = {
        'new': '-created_at',
        'price_asc': 'price',
        'price_desc': '-price',
        'name': 'name',
        'rating': '-rating',
    }
    products = products.order_by(sort_map.get(sort, '-created_at'))

    return render(
        request,
        'catalog/catalog.html',
        {
            'products': products,
            'categories': categories,
            'active_category': active_category,
            'active_tag': tag,
            'sort': sort,
            'search': search,
            'total': products.count(),
        },
    )


def item(request, slug):
    product = get_object_or_404(
        Product.objects.filter(is_active=True)
        .select_related('category')
        .prefetch_related('images', 'specifications', 'age_variants'),
        slug=slug,
    )
    gallery_images = list(product.images.all())
    age_variants = list(product.age_variants.all())
    related = (
        Product.objects.filter(category=product.category, is_active=True)
        .exclude(id=product.id)
        .select_related('category')[:4]
    )

    from reviews.models import Review

    reviews = Review.objects.filter(product=product, is_approved=True).order_by('-created_at')
    return render(
        request,
        'catalog/item.html',
        {
            'product': product,
            'gallery_images': gallery_images,
            'age_variants': age_variants,
            'related_products': related,
            'reviews': reviews,
        },
    )


@ensure_csrf_cookie
def bag(request):
    cart = get_cart(request)
    items, total, count = build_cart_items(cart)
    prices_json = json.dumps({item['cart_key']: round(float(item['price'])) for item in items})
    return render(
        request,
        'catalog/bag.html',
        {
            'items': items,
            'total': total,
            'count': count,
            'prices_json': prices_json,
        },
    )


def checkout(request):
    cart = get_cart(request)
    if not cart:
        return redirect('bag')

    items, total, _ = build_cart_items(cart)

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
                price=item['price'],
            )
        save_cart(request, {})
        return redirect('order_success')

    return render(
        request,
        'catalog/checkout.html',
        {
            'items': items,
            'total': total,
        },
    )


def order_success(request):
    return render(request, 'catalog/order_success.html')


def favorites(request):
    from reviews.models import Favorite

    session_id = request.session.session_key or ''
    if not session_id:
        request.session.create()
        session_id = request.session.session_key

    favs = Favorite.objects.filter(session_id=session_id).select_related('product__category')
    products = [fav.product for fav in favs if fav.product and fav.product.is_active]
    return render(request, 'catalog/favorites.html', {'products': products})


@require_POST
def cart_add(request):
    data = json.loads(request.body)
    slug = data.get('slug')
    qty = int(data.get('qty', 1))
    age_years = data.get('age_years')
    cart_key = f'{slug}|{age_years}' if age_years else slug
    cart = get_cart(request)
    cart[cart_key] = cart.get(cart_key, 0) + qty
    save_cart(request, cart)
    return JsonResponse({'count': sum(cart.values()), 'cart': cart})


@require_POST
def cart_update(request):
    data = json.loads(request.body)
    cart_key = data.get('cart_key') or data.get('slug')
    qty = int(data.get('qty', 1))
    cart = get_cart(request)

    if qty <= 0:
        cart.pop(cart_key, None)
    else:
        cart[cart_key] = qty
    save_cart(request, cart)

    _, total, _ = build_cart_items(cart)
    return JsonResponse({'count': sum(cart.values()), 'cart': cart, 'total': str(total)})


@require_POST
def cart_remove(request):
    data = json.loads(request.body)
    cart_key = data.get('cart_key') or data.get('slug')
    cart = get_cart(request)
    cart.pop(cart_key, None)
    save_cart(request, cart)
    return JsonResponse({'count': sum(cart.values()), 'cart': cart})


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
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        tag = self.request.query_params.get('tag')
        featured = self.request.query_params.get('featured')

        if category:
            queryset = queryset.filter(category__slug=category)
        if tag:
            queryset = queryset.filter(tags__icontains=tag)
        if featured:
            queryset = queryset.filter(is_featured=True)
        return queryset

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
