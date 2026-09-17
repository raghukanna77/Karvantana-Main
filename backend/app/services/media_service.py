"""Media storage (blueprint §56).

Files never live in the database: bytes go to storage (local dir in dev, S3 in
prod — same interface), DB keeps metadata + URLs. Uploads are validated for
MIME, extension and size; signatures/signed URLs noted for the S3 backend.
"""

from __future__ import annotations

import hashlib
import os
import uuid

from app.core.config import get_settings
from app.core.errors import ValidationFailedError

ALLOWED_MIME = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

_MIN_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG_SOI = b"\xff\xd8\xff"


def sniff_image_mime(data: bytes) -> str:
    """Content-sniff the real type — never trust the client-declared MIME."""
    if data[:3] == _JPEG_SOI:
        return "image/jpeg"
    if data[:8] == _MIN_PNG:
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def _local_media_dir() -> str:
    base = get_settings().MEDIA_DIR
    os.makedirs(base, exist_ok=True)
    return base


def save_media_bytes(data: bytes, prefix: str, ext: str) -> str:
    """Persist bytes and return the public relative URL."""
    name = f"{prefix}_{uuid.uuid4().hex[:12]}.{ext}"
    path = os.path.join(_local_media_dir(), name)
    with open(path, "wb") as fh:
        fh.write(data)
    return f"/media/{name}"


def store_upload(data: bytes, *, prefix: str = "img") -> dict:
    """Validate + store an image upload. Returns {url, mime, size, sha256}."""
    if len(data) == 0:
        raise ValidationFailedError("The file is empty. Please choose a photo.")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValidationFailedError("Please upload an image smaller than 10 MB.", code="PRODUCT_IMAGE_TOO_LARGE")
    mime = sniff_image_mime(data)
    if mime not in ALLOWED_MIME:
        raise ValidationFailedError("Please upload a JPG, PNG or WebP photo.", code="UNSUPPORTED_FILE_TYPE")
    ext = ALLOWED_MIME[mime]
    url = save_media_bytes(data, prefix, ext)
    return {"url": url, "mime": mime, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
