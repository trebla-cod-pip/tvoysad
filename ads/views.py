import hashlib

from django.shortcuts import get_object_or_404, redirect

from .models import AdCampaign, AdClick


def track_redirect(request, code):
    campaign = get_object_or_404(AdCampaign, code=code, is_active=True)

    ip = (request.META.get('HTTP_X_FORWARDED_FOR', '')
          .split(',')[0].strip()
          or request.META.get('REMOTE_ADDR', ''))
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]

    AdClick.objects.create(
        campaign=campaign,
        ip_hash=ip_hash,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
        referrer=request.META.get('HTTP_REFERER', '')[:500],
    )

    return redirect(campaign.get_destination_with_utm())
