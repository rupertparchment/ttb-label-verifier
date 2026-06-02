"""TTB Label Verification API — proof-of-concept for compliance review."""

import asyncio
import base64
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from .matcher import overall_status, verify_label
from .models import ApplicationData, BatchVerificationResponse, CheckStatus, FieldCheck, VerificationResult
from .ocr import extract_text_from_image

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="TTB Label Verifier",
    description="AI-powered alcohol label verification prototype",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_executor = ThreadPoolExecutor(max_workers=4)


def _thumbnail_b64(image: Image.Image, max_size: int = 200) -> str:
    thumb = image.copy()
    thumb.thumbnail((max_size, max_size))
    buf = io.BytesIO()
    thumb.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def _process_single(
    filename: str,
    image_bytes: bytes,
    application: ApplicationData,
) -> VerificationResult:
    start = time.perf_counter()
    try:
        image = Image.open(io.BytesIO(image_bytes))
        extracted_text, _, _ = extract_text_from_image(image)
        checks = verify_label(application, extracted_text)
        status = overall_status(checks)
        preview = _thumbnail_b64(image)
    except Exception as exc:
        checks = []
        status = CheckStatus.FAIL
        extracted_text = ""
        preview = None
        return VerificationResult(
            filename=filename,
            overall_status=status,
            checks=[
                FieldCheck(
                    field_name="Processing",
                    expected="Valid image",
                    found=None,
                    status=CheckStatus.FAIL,
                    message=f"Failed to process image: {exc}",
                    confidence=0.0,
                )
            ],
            extracted_text=extracted_text,
            processing_time_ms=int((time.perf_counter() - start) * 1000),
            image_preview=preview,
        )

    elapsed = int((time.perf_counter() - start) * 1000)
    return VerificationResult(
        filename=filename,
        overall_status=status,
        checks=checks,
        extracted_text=extracted_text,
        processing_time_ms=elapsed,
        image_preview=preview,
    )


async def _process_async(
    filename: str,
    image_bytes: bytes,
    application: ApplicationData,
) -> VerificationResult:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, _process_single, filename, image_bytes, application
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ttb-label-verifier"}


def _is_image_upload(upload: UploadFile) -> bool:
    """Accept standard image types; Windows often sends application/octet-stream."""
    if upload.content_type and upload.content_type.startswith("image/"):
        return True
    name = (upload.filename or "").lower()
    return name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"))


@app.post("/api/verify", response_model=VerificationResult)
async def verify_single(
    image: UploadFile = File(...),
    brand_name: str = Form(...),
    class_type: str = Form(""),
    alcohol_content: str = Form(""),
    net_contents: str = Form(""),
    government_warning: str = Form(""),
    bottler_producer: str = Form(""),
    country_of_origin: str = Form(""),
):
    """Verify a single label image against application data."""
    if not _is_image_upload(image):
        raise HTTPException(400, "File must be an image (JPEG, PNG, etc.)")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(400, "Uploaded file is empty.")

    application = ApplicationData(
        brand_name=brand_name,
        class_type=class_type,
        alcohol_content=alcohol_content,
        net_contents=net_contents,
        government_warning=government_warning,
        bottler_producer=bottler_producer,
        country_of_origin=country_of_origin,
    )
    return await _process_async(
        filename=image.filename or "label.jpg",
        image_bytes=image_bytes,
        application=application,
    )


@app.post("/api/verify/batch", response_model=BatchVerificationResponse)
async def verify_batch(
    images: list[UploadFile] = File(...),
    applications_json: str = Form(...),
):
    """
    Batch verify multiple labels.
    applications_json: JSON array of ApplicationData objects, one per image (same order).
    """
    try:
        apps_raw = json.loads(applications_json)
        applications = [ApplicationData(**a) for a in apps_raw]
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(400, f"Invalid applications_json: {exc}") from exc

    if len(applications) != len(images):
        raise HTTPException(
            400,
            f"Expected {len(images)} application records, got {len(applications)}",
        )

    start = time.perf_counter()
    tasks = []
    for img, app_data in zip(images, applications):
        if not _is_image_upload(img):
            raise HTTPException(400, f"File must be an image: {img.filename}")
        image_bytes = await img.read()
        if not image_bytes:
            raise HTTPException(400, f"Uploaded file is empty: {img.filename}")
        tasks.append(
            _process_async(
                filename=img.filename or "label.jpg",
                image_bytes=image_bytes,
                application=app_data,
            )
        )

    results = await asyncio.gather(*tasks)
    elapsed = int((time.perf_counter() - start) * 1000)

    passed = sum(1 for r in results if r.overall_status == CheckStatus.PASS)
    failed = sum(1 for r in results if r.overall_status == CheckStatus.FAIL)
    warnings = sum(1 for r in results if r.overall_status == CheckStatus.WARNING)

    return BatchVerificationResponse(
        results=list(results),
        total=len(results),
        passed=passed,
        failed=failed,
        warnings=warnings,
        total_processing_time_ms=elapsed,
    )


# Serve built frontend in production (Docker)
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(404)
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(404)
