def cart_context(request):
    cart = request.session.get('cart', {})
    return {'cart_count': sum(cart.values())}
