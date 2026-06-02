"""End-to-end OCR verification against sample labels."""

import json
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.matcher import overall_status, verify_label
from app.models import ApplicationData
from app.ocr import extract_text_from_image

SAMPLES = Path(__file__).resolve().parent.parent / "sample_labels"


def main():
    manifest = json.loads((SAMPLES / "manifest.json").read_text())
    for item in manifest:
        path = SAMPLES / item["filename"]
        img = Image.open(path)
        start = time.perf_counter()
        text, conf, method = extract_text_from_image(img)
        elapsed = int((time.perf_counter() - start) * 1000)
        app = ApplicationData(**item["application"])
        checks = verify_label(app, text)
        status = overall_status(checks)
        expected = item["expected_result"]
        ok = status.value == expected or (expected == "fail" and status.value in ("fail", "warning"))
        mark = "OK" if ok else "MISMATCH"
        print(f"[{mark}] {item['filename']}: {status.value} (expected {expected}) — {elapsed}ms via {method}")
        if not ok:
            for c in checks:
                print(f"  {c.field_name}: {c.status.value} — {c.message}")


if __name__ == "__main__":
    main()
