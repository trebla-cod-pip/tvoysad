from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib import admin

from .admin import _build_dashboard_context


@staff_member_required
def dashboard(request):
    ctx = _build_dashboard_context(request, admin.site)
    return render(request, 'admin/activity/dashboard.html', ctx)
