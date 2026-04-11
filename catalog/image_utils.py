"""
WebP thumbnail generation for Category and Product images.

Thumbnails are stored at:
  MEDIA_ROOT/thumbs/<original_relative_path>/<stem>_w<width>.webp
"""

import threading
from pathlib import Path

from django.conf import settings

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


THUMB_WIDTHS = [160, 240, 320, 480, 640, 800, 1200]
THUMB_QUALITY = 82


def normalize_widths(widths=None) -> list[int]:
    """
    Normalise widths passed from templates/commands.

    Supported formats:
    - None -> default THUMB_WIDTHS
    - int -> [int]
    - "320,640,1200" string
    - iterable of ints/strings
    """
    if widths is None:
        return THUMB_WIDTHS

    if isinstance(widths, int):
        return [widths] if widths > 0 else THUMB_WIDTHS

    if isinstance(widths, str):
        raw_values = [chunk.strip() for chunk in widths.split(',')]
    else:
        raw_values = list(widths)

    parsed: list[int] = []
    for value in raw_values:
        try:
            width = int(value)
        except (TypeError, ValueError):
            continue
        if width > 0:
            parsed.append(width)

    if not parsed:
        return THUMB_WIDTHS

    return sorted(set(parsed))


def thumb_fs_path(image_name: str, width: int) -> Path:
    """Absolute filesystem path for a thumbnail."""
    path = Path(image_name)
    return Path(settings.MEDIA_ROOT) / 'thumbs' / path.parent / f'{path.stem}_w{width}.webp'


def thumb_url(image_name: str, width: int) -> str:
    """Media URL for a thumbnail."""
    path = Path(image_name)
    rel = '/'.join(['thumbs', *path.parent.parts, f'{path.stem}_w{width}.webp'])
    return f'{settings.MEDIA_URL}{rel}'


def existing_webp_candidates(image_name: str, widths=None) -> list[tuple[int, str]]:
    """Return existing (width, url) WebP candidates for image_name."""
    candidates: list[tuple[int, str]] = []
    for width in normalize_widths(widths):
        if thumb_fs_path(image_name, width).exists():
            candidates.append((width, thumb_url(image_name, width)))
    return candidates


def generate_webp_thumbs(image_name: str, widths=None, force=False) -> dict[int, str]:
    """
    Generate WebP thumbnails for the given media image.

    Returns {width: url} for successfully processed widths.
    """
    if not PIL_AVAILABLE or not image_name:
        return {}

    source = Path(settings.MEDIA_ROOT) / image_name
    if not source.exists():
        return {}

    result: dict[int, str] = {}
    target_widths = normalize_widths(widths)

    try:
        with Image.open(source) as img:
            orig_w, orig_h = img.size

            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')

            for width in target_widths:
                dest = thumb_fs_path(image_name, width)
                if dest.exists() and not force:
                    result[width] = thumb_url(image_name, width)
                    continue

                dest.parent.mkdir(parents=True, exist_ok=True)

                if orig_w > width:
                    new_h = max(1, round(orig_h * width / orig_w))
                    thumb = img.copy()
                    thumb.thumbnail((width, new_h), Image.LANCZOS)
                else:
                    thumb = img.copy()

                save_kwargs = {
                    'format': 'WEBP',
                    'quality': THUMB_QUALITY,
                    'method': 4,  # 0-6, balanced compression/speed
                }
                if thumb.mode == 'RGBA':
                    save_kwargs['lossless'] = False

                thumb.save(str(dest), **save_kwargs)
                result[width] = thumb_url(image_name, width)

    except Exception:
        pass

    return result


def generate_webp_async(image_name: str, force=False):
    """Non-blocking wrapper that starts a daemon thread."""
    if image_name:
        thread = threading.Thread(
            target=generate_webp_thumbs,
            kwargs={'image_name': image_name, 'force': force},
            daemon=True,
        )
        thread.start()
