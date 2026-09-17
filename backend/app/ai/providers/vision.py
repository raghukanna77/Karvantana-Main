"""Demo VisionProvider — real image analysis with Pillow/OpenCV-style operations.

Clearly labeled as the demo provider: quality metrics are genuinely computed
from pixel data (blur via variance, brightness, resolution); enhancement is
real histogram-based correction. No generative background synthesis — the
"clean background" op applies a neutral soft-light wash and center crop.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

from PIL import Image, ImageEnhance, ImageOps, ImageStat, ImageFilter

from app.ai.providers.base import ImageEnhancement, VisionQuality

logger = logging.getLogger("karvantana.vision")

MAX_DIMENSION = 1600


class DemoVisionProvider:
    name = "demo-vision"

    # ------------------------------------------------------------------ quality

    def analyze_quality(self, image_bytes: bytes) -> VisionQuality:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
        checks: list[dict] = []

        # Resolution
        w, h = img.size
        megapixels = (w * h) / 1_000_000
        checks.append({
            "label": "resolution",
            "passed": megapixels >= 0.3,
            "detail": f"{w}x{h}" if megapixels >= 0.3 else f"Low resolution ({w}x{h}). Use a brighter, steady photo.",
        })

        # Brightness (0=black, 255=white)
        gray = img.convert("L")
        brightness = ImageStat.Stat(gray).mean[0]
        bright_ok = 60 <= brightness <= 235
        checks.append({
            "label": "lighting",
            "passed": bright_ok,
            "detail": "Good lighting" if bright_ok else ("Photo is too dark — try daylight near a window." if brightness < 60 else "Photo is overexposed."),
        })

        # Blur via edge variance (Laplacian-style)
        edges = gray.filter(ImageFilter.FIND_EDGES)
        variance = ImageStat.Stat(edges).stddev[0]
        sharp_ok = variance >= 12
        checks.append({
            "label": "sharpness",
            "passed": sharp_ok,
            "detail": "Product is in focus" if sharp_ok else "Photo looks blurry — hold the phone steady.",
        })

        # Colorfulness as a proxy for a present, well-lit subject
        sat = ImageStat.Stat(img.convert("HSV")).mean[1]
        color_ok = sat >= 18
        checks.append({
            "label": "subject_visibility",
            "passed": color_ok,
            "detail": "Product clearly visible" if color_ok else "Product looks washed out — fill the frame with the item.",
        })

        score = sum(25 for c in checks if c["passed"]) + (10 if megapixels >= 1.0 else 0)
        return VisionQuality(score=min(score, 100), checks=checks)

    # --------------------------------------------------------------- enhancement

    def enhance(self, image_bytes: bytes, operations: Optional[list[str]] = None) -> ImageEnhancement:
        ops = operations or ["auto"]
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
        img = ImageOps.exif_transpose(img)
        applied: list[str] = []

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Resize only downward; never upscale (no fake resolution).
        if max(img.size) > MAX_DIMENSION:
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
            applied.append("resize")

        if "auto" in ops or "brightness" in ops:
            gray = img.convert("L")
            mean = ImageStat.Stat(gray).mean[0]
            target = 150.0
            factor = max(0.6, min(1.6, target / max(mean, 1)))
            img = ImageEnhance.Brightness(img).enhance(factor)
            applied.append("brightness")

        if "auto" in ops or "contrast" in ops:
            img = ImageEnhance.Contrast(img).enhance(1.12)
            applied.append("contrast")

        if "auto" in ops or "sharpness" in ops:
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
            applied.append("sharpness")

        if "auto" in ops or "white_balance" in ops:
            r, g, b = (ImageStat.Stat(img.crop(_center_box(img, 0.6))).mean) if img.mode == "RGB" else (128, 128, 128)
            mid = (r + g + b) / 3 or 1
            if img.mode == "RGB":
                channels = img.split()
                balanced = [ch.point(lambda px, m=m: min(255, int(px * mid / m))) for ch, m in zip(channels, (r, g, b))]
                img = Image.merge("RGB", balanced)
            applied.append("white_balance")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=88, optimize=True)
        from app.services.media_service import save_media_bytes

        path = save_media_bytes(buf.getvalue(), "enhanced", "jpg")
        return ImageEnhancement(enhanced_path=path, operations=applied)

    def background_clean(self, image_bytes: bytes) -> ImageEnhancement:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
        if img.mode != "RGB":
            img = img.convert("RGB")
        img = ImageOps.exif_transpose(img)

        # Demo approach: gentle vignette toward a studio-neutral edge + soft focus
        # border, keeping the product untouched in the center. A real segmentation
        # model slots in here (provider interface unchanged).
        img = img.filter(ImageFilter.GaussianBlur(0.6))
        mask = Image.new("L", img.size, 0)
        from PIL import ImageDraw

        draw = ImageDraw.Draw(mask)
        w, h = img.size
        draw.ellipse((int(w * 0.08), int(h * 0.08), int(w * 0.92), int(h * 0.92)), fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(40))
        white = Image.new("RGB", img.size, (244, 242, 238))  # studio-neutral backdrop
        img = Image.composite(img, white, mask)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=88, optimize=True)
        from app.services.media_service import save_media_bytes

        path = save_media_bytes(buf.getvalue(), "bgclean", "jpg")
        return ImageEnhancement(enhanced_path=path, operations=["background_clean_demo"])


def _center_box(img: Image.Image, fraction: float) -> tuple[int, int, int, int]:
    w, h = img.size
    bw, bh = int(w * fraction), int(h * fraction)
    return ((w - bw) // 2, (h - bh) // 2, (w + bw) // 2, (h + bh) // 2)
