"""Label image OCR with preprocessing for speed and accuracy."""

import io
import os
import re
import time

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    # Common Windows install path (UB-Mannheim build)
    _win_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.name == "nt" and os.path.isfile(_win_tesseract):
        pytesseract.pytesseract.tesseract_cmd = _win_tesseract
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def _preprocess_image(image: Image.Image) -> Image.Image:
    """Enhance label image for OCR — handles glare, rotation, low contrast."""
    img = image.convert("RGB")

    # Auto-rotate based on EXIF if present
    img = ImageOps.exif_transpose(img)

    # Scale up small images for better OCR
    min_dim = min(img.size)
    if min_dim < 800:
        scale = 800 / min_dim
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Convert to grayscale and boost contrast
    gray = img.convert("L")
    enhanced = ImageEnhance.Contrast(gray).enhance(1.8)
    sharpened = enhanced.filter(ImageFilter.SHARPEN)

    return sharpened


def _ocr_region(image: Image.Image, config: str = "--psm 6") -> str:
    if not TESSERACT_AVAILABLE:
        return ""
    processed = _preprocess_image(image)
    return pytesseract.image_to_string(processed, config=config).strip()


def _extract_with_tesseract(image: Image.Image) -> tuple[str, float]:
    """Run Tesseract OCR. Returns (text, confidence estimate)."""
    if not TESSERACT_AVAILABLE:
        return "", 0.0

    # Full label
    text = _ocr_region(image, "--psm 6 -c preserve_interword_spaces=1")
    text_alt = _ocr_region(image, "--psm 3")
    combined = text if len(text) >= len(text_alt) else text_alt

    # Bottom region — government warning is often small; re-OCR at higher zoom
    w, h = image.size
    bottom = image.crop((0, int(h * 0.55), w, h))
    bottom_big = bottom.resize((bottom.width * 2, bottom.height * 2), Image.Resampling.LANCZOS)
    bottom_text = _ocr_region(bottom_big, "--psm 6")
    if bottom_text:
        combined = combined + "\n" + bottom_text

    alpha_ratio = len(re.findall(r"[a-zA-Z0-9]", combined)) / max(len(combined), 1)
    confidence = min(0.95, 0.5 + alpha_ratio * 0.5)

    return combined.strip(), confidence


def _extract_with_openai(image: Image.Image) -> tuple[str, float]:
    """Optional OpenAI Vision fallback for difficult images."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or not OPENAI_AVAILABLE:
        return "", 0.0

    client = OpenAI(api_key=api_key)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    import base64
    b64 = base64.b64encode(buf.getvalue()).decode()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract ALL text visible on this alcohol beverage label. "
                            "Return the raw text exactly as it appears, preserving "
                            "capitalization and line breaks. Include brand name, class/type, "
                            "alcohol content, net contents, bottler info, and the full "
                            "government warning statement."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
        max_tokens=1500,
    )
    text = response.choices[0].message.content or ""
    return text.strip(), 0.92


def extract_text_from_image(
    image: Image.Image,
    use_openai_fallback: bool = True,
) -> tuple[str, float, str]:
    """
    Extract text from a label image.
    Returns (text, confidence, method_used).
    """
    start = time.perf_counter()

    text, confidence = _extract_with_tesseract(image)
    method = "tesseract"

    # Use OpenAI if Tesseract result is weak and API key is available
    if use_openai_fallback and confidence < 0.6 and os.environ.get("OPENAI_API_KEY"):
        ai_text, ai_conf = _extract_with_openai(image)
        if len(ai_text) > len(text):
            text, confidence = ai_text, ai_conf
            method = "openai-vision"

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return text, confidence, method
