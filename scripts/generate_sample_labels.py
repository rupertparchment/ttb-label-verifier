"""Generate sample alcohol label images for testing."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

STANDARD_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "sample_labels"


def _get_font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def create_label(
    brand: str,
    class_type: str,
    abv: str,
    net_contents: str,
    bottler: str,
    warning: str = STANDARD_WARNING,
    bg_color: tuple = (245, 230, 200),
    fail_warning: bool = False,
    origin: str = "",
) -> Image.Image:
    """Create a realistic-looking spirits label."""
    w, h = 600, 800
    img = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(img)

    # Decorative border
    draw.rectangle([20, 20, w - 20, h - 20], outline=(80, 50, 20), width=3)

    font_brand = _get_font(36, bold=True)
    font_class = _get_font(22)
    font_body = _get_font(18)
    font_warning = _get_font(13, bold=True)
    font_small = _get_font(14)

    y = 60
    draw.text((w // 2, y), brand, fill=(40, 25, 10), font=font_brand, anchor="mt")
    y += 60
    draw.text((w // 2, y), class_type, fill=(60, 40, 20), font=font_class, anchor="mt")
    y += 50
    draw.text((w // 2, y), abv, fill=(40, 25, 10), font=font_body, anchor="mt")
    y += 40
    draw.text((w // 2, y), net_contents, fill=(40, 25, 10), font=font_body, anchor="mt")
    y += 40
    if origin:
        draw.text((w // 2, y), origin, fill=(60, 40, 20), font=font_small, anchor="mt")
        y += 30
    y += 20
    for line in bottler.split("\n"):
        draw.text((w // 2, y), line.strip(), fill=(80, 60, 40), font=font_small, anchor="mt")
        y += 22

    # Government warning at bottom — word-wrapped for readability
    display_warning = warning
    if fail_warning:
        display_warning = warning.replace("GOVERNMENT WARNING:", "Government Warning:")

    warning_y = h - 200
    max_width = w - 80
    words = display_warning.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font_warning)
        if bbox[2] - bbox[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))

    for line in lines:
        draw.text((40, warning_y), line, fill=(20, 20, 20), font=font_warning)
        warning_y += 18

    return img


SAMPLES = [
    {
        "filename": "old_tom_distillery_pass.png",
        "application": {
            "brand_name": "OLD TOM DISTILLERY",
            "class_type": "Kentucky Straight Bourbon Whiskey",
            "alcohol_content": "45% Alc./Vol. (90 Proof)",
            "net_contents": "750 mL",
            "bottler_producer": "Old Tom Distillery, Louisville, KY",
            "government_warning": STANDARD_WARNING,
        },
        "label": {
            "brand": "OLD TOM DISTILLERY",
            "class_type": "Kentucky Straight Bourbon Whiskey",
            "abv": "45% Alc./Vol. (90 Proof)",
            "net_contents": "750 mL",
            "bottler": "Distilled and Bottled by\nOld Tom Distillery, Louisville, KY",
        },
    },
    {
        "filename": "stones_throw_fuzzy_pass.png",
        "application": {
            "brand_name": "Stone's Throw",
            "class_type": "Small Batch Gin",
            "alcohol_content": "44% Alc./Vol.",
            "net_contents": "750 mL",
            "bottler_producer": "Stone's Throw Spirits, Portland, OR",
            "government_warning": STANDARD_WARNING,
        },
        "label": {
            "brand": "STONE'S THROW",  # Dave's case — different casing
            "class_type": "Small Batch Gin",
            "abv": "44% Alc./Vol.",
            "net_contents": "750 mL",
            "bottler": "Stone's Throw Spirits\nPortland, Oregon",
        },
    },
    {
        "filename": "glenmore_import_pass.png",
        "application": {
            "brand_name": "GLENMORE HIGHLAND",
            "class_type": "Blended Scotch Whisky",
            "alcohol_content": "40% Alc./Vol. (80 Proof)",
            "net_contents": "1 L",
            "bottler_producer": "Imported by Atlantic Spirits Co., Baltimore, MD",
            "country_of_origin": "Product of Scotland",
            "government_warning": STANDARD_WARNING,
        },
        "label": {
            "brand": "GLENMORE HIGHLAND",
            "class_type": "Blended Scotch Whisky",
            "abv": "40% Alc./Vol. (80 Proof)",
            "net_contents": "1 L",
            "origin": "Product of Scotland",
            "bottler": "Imported by Atlantic Spirits Co.\nBaltimore, MD",
            "bg_color": (230, 235, 245),
        },
    },
    {
        "filename": "bad_warning_fail.png",
        "application": {
            "brand_name": "Riverside Vodka",
            "class_type": "Premium Vodka",
            "alcohol_content": "40% Alc./Vol. (80 Proof)",
            "net_contents": "1 L",
            "bottler_producer": "Riverside Distilling Co.",
            "government_warning": STANDARD_WARNING,
        },
        "label": {
            "brand": "RIVERSIDE VODKA",
            "class_type": "Premium Vodka",
            "abv": "40% Alc./Vol. (80 Proof)",
            "net_contents": "1 L",
            "bottler": "Riverside Distilling Co.",
            "fail_warning": True,
        },
    },
    {
        "filename": "abv_mismatch_fail.png",
        "application": {
            "brand_name": "Mountain Peak Rye",
            "class_type": "Straight Rye Whiskey",
            "alcohol_content": "46% Alc./Vol.",
            "net_contents": "750 mL",
            "bottler_producer": "Mountain Peak Distillery",
            "government_warning": STANDARD_WARNING,
        },
        "label": {
            "brand": "MOUNTAIN PEAK RYE",
            "class_type": "Straight Rye Whiskey",
            "abv": "43% Alc./Vol.",  # Wrong ABV
            "net_contents": "750 mL",
            "bottler": "Mountain Peak Distillery",
        },
    },
]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    for sample in SAMPLES:
        label_kwargs = dict(sample["label"])
        fail_warning = label_kwargs.pop("fail_warning", False)
        img = create_label(**label_kwargs, fail_warning=fail_warning)
        path = OUTPUT_DIR / sample["filename"]
        img.save(path)
        manifest.append({
            "filename": sample["filename"],
            "application": sample["application"],
            "expected_result": "pass" if "pass" in sample["filename"] else "fail",
        })
        print(f"Created {path}")

    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
