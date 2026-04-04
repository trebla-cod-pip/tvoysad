import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Page, ContactMessage


def contact_page(request):
    success = False
    if request.method == 'POST':
        ContactMessage.objects.create(
            name=request.POST.get('name', ''),
            contact=request.POST.get('contact', ''),
            message=request.POST.get('message', ''),
        )
        success = True
    return render(request, 'pages/contact.html', {'success': success})


@require_POST
def contact_submit(request):
    data = json.loads(request.body)
    ContactMessage.objects.create(
        name=data.get('name', ''),
        contact=data.get('contact', ''),
        message=data.get('message', ''),
    )
    return JsonResponse({'ok': True})


def delivery_page(request):
    return render(request, 'pages/delivery.html')


def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, is_published=True)
    return render(request, 'pages/page.html', {'page': page})
