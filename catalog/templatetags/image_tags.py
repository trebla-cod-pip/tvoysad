from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from catalog.image_utils import (
    THUMB_WIDTHS,
    existing_webp_candidates,
    generate_webp_async,
    normalize_widths,
)

register = template.Library()


def _parse_bool(value, default=True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {'', '0', 'false', 'no', 'off'}:
            return False
        if lowered in {'1', 'true', 'yes', 'on'}:
            return True
    return bool(value)


def _best_candidate(candidates: list[tuple[int, str]], preferred_width: int) -> str:
    larger_or_equal = [candidate for candidate in candidates if candidate[0] >= preferred_width]
    if larger_or_equal:
        return min(larger_or_equal, key=lambda item: item[0])[1]
    return max(candidates, key=lambda item: item[0])[1]


@register.simple_tag
def webp_best_url(image_field, preferred_width=800, widths=None):
    """
    Return the best existing WebP URL for given width.

    Falls back to original image URL if no WebP thumbs exist yet.
    """
    if not image_field:
        return ''

    image_name = image_field.name
    width_list = normalize_widths(widths)
    candidates = existing_webp_candidates(image_name, widths=width_list)

    if not candidates:
        generate_webp_async(image_name)
        return image_field.url

    try:
        target_width = int(preferred_width)
    except (TypeError, ValueError):
        target_width = THUMB_WIDTHS[-1]

    return _best_candidate(candidates, target_width)


@register.simple_tag
def webp_picture(
    image_field,
    alt='',
    sizes='100vw',
    lazy=True,
    fetch_priority='',
    widths=None,
    img_class='',
    img_id='',
):
    """
    Render a <picture> element with WebP srcset and original-format fallback.
    """
    if not image_field:
        return ''

    image_name = image_field.name
    width_list = normalize_widths(widths)
    candidates = existing_webp_candidates(image_name, widths=width_list)

    if not candidates:
        generate_webp_async(image_name)

    loading_value = 'lazy' if _parse_bool(lazy, default=True) else 'eager'
    escaped_alt = conditional_escape(alt or '')
    escaped_sizes = conditional_escape(sizes or '100vw')
    escaped_src = conditional_escape(image_field.url)
    escaped_class = conditional_escape(img_class) if img_class else ''
    escaped_id = conditional_escape(img_id) if img_id else ''
    escaped_fetch_priority = conditional_escape(fetch_priority) if fetch_priority else ''

    width_attr = ''
    height_attr = ''
    try:
        width_attr = f' width="{int(image_field.width)}"'
        height_attr = f' height="{int(image_field.height)}"'
    except Exception:
        pass

    class_attr = f' class="{escaped_class}"' if escaped_class else ''
    id_attr = f' id="{escaped_id}"' if escaped_id else ''
    fetch_priority_attr = (
        f' fetchpriority="{escaped_fetch_priority}"'
        if escaped_fetch_priority
        else ''
    )

    img_tag = (
        f'<img src="{escaped_src}" alt="{escaped_alt}"'
        f' loading="{loading_value}" decoding="async"'
        f'{width_attr}{height_attr}{class_attr}{id_attr}{fetch_priority_attr}>'
    )

    if not candidates:
        return mark_safe(img_tag)

    srcset = ', '.join(f'{url} {width}w' for width, url in candidates)
    picture_tag = (
        '<picture>'
        f'<source type="image/webp" srcset="{srcset}" sizes="{escaped_sizes}">'
        f'{img_tag}'
        '</picture>'
    )
    return mark_safe(picture_tag)
