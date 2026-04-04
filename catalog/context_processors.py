def cart_context(request):
    from pages.models import SiteSettings
    cart = request.session.get('cart', {})
    return {
        'cart_count': sum(cart.values()),
        'site_settings': SiteSettings.get(),
    }
