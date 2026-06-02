"""Unit tests for label field matching (no OCR required)."""

from app.constants import STANDARD_GOVERNMENT_WARNING
from app.matcher import (
    _check_alcohol_content,
    _check_brand_name,
    _check_government_warning,
    overall_status,
    verify_label,
)
from app.models import ApplicationData, CheckStatus


def test_brand_fuzzy_match_stones_throw():
    """Dave's scenario: STONE'S THROW on label vs Stone's Throw in application."""
    result = _check_brand_name(
        "Stone's Throw",
        "STONE'S THROW\nSmall Batch Gin\n44% Alc./Vol.",
    )
    assert result.status == CheckStatus.PASS


def test_brand_mismatch():
    result = _check_brand_name("Wrong Brand", "OLD TOM DISTILLERY Bourbon")
    assert result.status == CheckStatus.FAIL


def test_abv_match():
    result = _check_alcohol_content(
        "45% Alc./Vol. (90 Proof)",
        "Kentucky Bourbon 45% Alc./Vol. 90 Proof",
    )
    assert result.status == CheckStatus.PASS


def test_abv_mismatch():
    result = _check_alcohol_content("46% Alc./Vol.", "43% Alc./Vol.")
    assert result.status == CheckStatus.FAIL


def test_government_warning_pass():
    result = _check_government_warning(STANDARD_GOVERNMENT_WARNING, STANDARD_GOVERNMENT_WARNING)
    assert result.status == CheckStatus.PASS


def test_government_warning_wrong_case_fail():
    """Jenny's scenario: title case instead of ALL CAPS."""
    bad = STANDARD_GOVERNMENT_WARNING.replace("GOVERNMENT WARNING:", "Government Warning:")
    result = _check_government_warning(STANDARD_GOVERNMENT_WARNING, bad)
    assert result.status == CheckStatus.FAIL


def test_full_verification_pass():
    app = ApplicationData(
        brand_name="OLD TOM DISTILLERY",
        class_type="Kentucky Straight Bourbon Whiskey",
        alcohol_content="45% Alc./Vol.",
        net_contents="750 mL",
        government_warning=STANDARD_GOVERNMENT_WARNING,
    )
    label_text = """
    OLD TOM DISTILLERY
    Kentucky Straight Bourbon Whiskey
    45% Alc./Vol. (90 Proof)
    750 mL
    """ + STANDARD_GOVERNMENT_WARNING

    checks = verify_label(app, label_text)
    assert overall_status(checks) == CheckStatus.PASS
