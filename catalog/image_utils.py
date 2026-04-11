"""
WebP thumbnail generation for Category and Product images.

Thumbnails are stored at:
  MEDIA_ROOT/thumbs/<original_relative_path>/<stem>_w<width>.webp

Example:
  Original:  media/categories/grusha.jpg
  Thumb 400: media/thumbs/categories/grusha_w400.webp
  Thumb 800: media/thumbs/categories/grusha_w800.webp
"""
import threading
from pathlib import Path

from django.conf import settings

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

THUMB_WIDTHS  = [400, 800]
THUMB_QUALITY = 85   # 0-100; 85 is good balance size/quality for photos


# ─────────────────────────────────────────────────────────────────────────────
# Path helpers
# ─────────────────────────────────────────────────────────────────────────────

def thumb_fs_path(image_name: str, width: int) -> Path:
    """Absolute filesystem path for a thumbnail."""
    p = Path(image_name)
    return Path(settings.MEDIA_ROOT) / 'thumbs' / p.parent / f'{p.stem}_w{width}.webp'


def thumb_url(image_name: str, width: int) -> str:
    """Media URL for a thumbnail."""
    p = Path(image_name)
    # Use forward slashes regardless of OS
    rel = '/'.join(['thumbs', *p.parent.parts, f'{p.stem}_w{width}.webp'])
    return f'{settings.MEDIA_URL}{rel}'


# ─────────────────────────────────────────────────────────────────────────────
# Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_webp_thumbs(image_name: str, widths=None, force=False) -> dict[int, str]:
    """
    Generate WebP thumbnails for the given media image.

    Returns {width: url} for successfully processed widths.
    Skips widths whose thumb already exists (unless force=True).
    Does nothing and returns {} if Pillow isn't installed or file missing.
    """
    if not PIL_AVAILABLE or not image_name:
        return {}

    widths = widths or THUMB_WIDTHS
    source = Path(settings.MEDIA_ROOT) / image_name

    if not source.exists():
        return {}

    result: dict[int, str] = {}

    try:
        with Image.open(source) as img:
            orig_w, orig_h = img.size

            # Normalise mode
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')

            for w in widths:
                dest = thumb_fs_path(image_name, w)
                if dest.exists() and not force:
                    result[w] = thumb_url(image_name, w)
                    continue

                dest.parent.mkdir(parents=True, exist_ok=True)

                # Calculate proportional height; never upscale
                if orig_w > w:
                    h = max(1, round(orig_h * w / orig_w))
                    thumb = img.copy()
                    thumb.thumbnail((w, h), Image.LANCZOS)
                else:
                    thumb = img.copy()

                save_kw = {
                    'format':  'WEBP',
                    'quality': THUMB_QUALITY,
                    'method':  4,   # 0-6; 4 is a good tradeoff encode speed/compression
                }
                # RGBA: keep alpha channel (lossless for transparency areas)
                if thumb.mode == 'RGBA':
                    save_kw['lossless'] = False

                thumb.save(str(dest), **save_kw)
                result[w] = thumb_url(image_name, w)

    except Exception:
        pass   # Image errors must never crash the app

    return result


def generate_webp_async(image_name: str, force=False):
    """Non-blocking wrapper — fires a daemon thread."""
    if image_name:
        t = threading.Thread(
            target=generate_webp_thumbs,
            kwargs={'image_name': image_name, 'force': force},
            daemon=True,
        )
        t.start()
