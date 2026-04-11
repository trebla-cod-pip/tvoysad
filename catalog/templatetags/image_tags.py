from django import template
from django.utils.html import format_html

from catalog.image_utils import thumb_fs_path, thumb_url, THUMB_WIDTHS

register = template.Library()


@register.simple_tag
def webp_picture(image_field, alt='', sizes='100vw',
                 lazy=True, fetch_priority='', widths=None):
    """
    Render a <picture> element with WebP srcset and original-format fallback.

    Usage:
        {% load image_tags %}
        {% webp_picture product.image alt=product.name sizes="50vw" %}
        {% webp_picture site_settings.hero_image alt="Hero" lazy=False fetch_priority="high" %}

    Falls back to plain <img> if image_field is empty.
    If WebP thumbs don't exist yet, renders srcset with original URL only
    (thumbs will be generated asynchronously on save).
    """
    if not image_field:
        return ''

    widths = widths or THUMB_WIDTHS
    image_name = image_field.name

    # Build srcset only for widths whose thumb file actually exists
    srcset_parts = []
    for w in widths:
        path = thumb_fs_path(image_name, w)
        if path.exists():
            srcset_parts.append(f'{thumb_url(image_name, w)} {w}w')

    loading_attr    = 'lazy' if lazy else 'eager'
    fp_attr         = f' fetchpriority="{fetch_priority}"' if fetch_priority else ''
    alt_escaped     = alt.replace('"', '&quot;')
    src             = image_field.url

    if srcset_parts:
        srcset = ', '.join(srcset_parts)
        html = (
            f'<picture>'
            f'<source type="image/webp" srcset="{srcset}" sizes="{sizes}">'
            f'<img src="{src}" alt="{alt_escaped}" loading="{loading_attr}"{fp_attr}>'
            f'</picture>'
        )
    else:
        # Thumbs not ready yet — render plain img
        html = f'<img src="{src}" alt="{alt_escaped}" loading="{loading_attr}"{fp_attr}>'

    # format_html isn't used here because we've already escaped manually;
    # mark_safe is appropriate since src/alt are from trusted field values.
    from django.utils.safestring import mark_safe
    return mark_safe(html)
