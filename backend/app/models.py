from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"


class FieldCheck(BaseModel):
    field_name: str
    expected: str
    found: Optional[str] = None
    status: CheckStatus
    message: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class ApplicationData(BaseModel):
    brand_name: str
    class_type: str = ""
    alcohol_content: str = ""
    net_contents: str = ""
    government_warning: str = ""
    bottler_producer: str = ""
    country_of_origin: str = ""


class VerificationResult(BaseModel):
    filename: str
    overall_status: CheckStatus
    checks: list[FieldCheck]
    extracted_text: str = ""
    processing_time_ms: int = 0
    image_preview: Optional[str] = None  # base64 thumbnail


class BatchVerificationResponse(BaseModel):
    results: list[VerificationResult]
    total: int
    passed: int
    failed: int
    warnings: int
    total_processing_time_ms: int
