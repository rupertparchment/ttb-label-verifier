"""Field matching logic for TTB label verification."""

import re
from typing import Optional

from rapidfuzz import fuzz

from .constants import STANDARD_GOVERNMENT_WARNING
from .models import ApplicationData, CheckStatus, FieldCheck


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s%./]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_brand(text: str) -> str:
    """Normalize brand name — handles case, punctuation, apostrophes."""
    text = text.lower().strip()
    text = text.replace("'", "'").replace("'", "'")
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_abv_values(text: str) -> set[str]:
    """Extract ABV/proof numbers from text."""
    values: set[str] = set()
    # 45% Alc./Vol., 45% ABV, 90 Proof, 45% alc/vol
    for match in re.finditer(
        r"(\d+(?:\.\d+)?)\s*%\s*(?:alc\.?\/?\s*vol\.?|abv|alc/vol)",
        text,
        re.IGNORECASE,
    ):
        values.add(match.group(1))
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*proof", text, re.IGNORECASE):
        proof = float(match.group(1))
        values.add(str(proof / 2))
    # Standalone percentage near alcohol context
    if re.search(r"alc|proof|abv|vol", text, re.IGNORECASE):
        for match in re.finditer(r"(\d+(?:\.\d+)?)\s*%", text):
            values.add(match.group(1))
    return values


def _extract_volume(text: str) -> set[str]:
    """Extract net contents values."""
    values: set[str] = set()
    for match in re.finditer(
        r"(\d+(?:\.\d+)?)\s*(ml|mL|l|L|oz|fl\.?\s*oz\.?)",
        text,
        re.IGNORECASE,
    ):
        amount, unit = match.group(1), match.group(2).lower().replace(".", "").replace(" ", "")
        values.add(f"{amount}{unit}")
        # Normalize ml
        if unit in ("ml",):
            values.add(f"{amount}ml")
        if unit in ("l",) and float(amount) < 10:
            values.add(f"{int(float(amount) * 1000)}ml")
    return values


def _find_in_text(needle: str, haystack: str, fuzzy_threshold: int = 85) -> tuple[bool, Optional[str], float]:
    """Find needle in haystack with fuzzy matching. Returns (found, matched_text, score)."""
    if not needle or not haystack:
        return False, None, 0.0

    norm_needle = _normalize_text(needle)
    norm_hay = _normalize_text(haystack)

    if norm_needle in norm_hay:
        return True, needle, 100.0

    # Sliding window fuzzy match for multi-word fields
    needle_words = norm_needle.split()
    hay_words = norm_hay.split()
    if len(needle_words) <= len(hay_words):
        window = len(needle_words)
        best_score = 0.0
        best_match = None
        for i in range(len(hay_words) - window + 1):
            chunk = " ".join(hay_words[i : i + window])
            score = fuzz.ratio(norm_needle, chunk)
            if score > best_score:
                best_score = score
                best_match = chunk
        if best_score >= fuzzy_threshold:
            return True, best_match, best_score

    ratio = fuzz.partial_ratio(norm_needle, norm_hay)
    if ratio >= fuzzy_threshold:
        return True, needle, ratio

    token_set = fuzz.token_set_ratio(norm_needle, norm_hay)
    return token_set >= fuzzy_threshold, None, max(ratio, token_set)


def _check_brand_name(expected: str, extracted_text: str) -> FieldCheck:
    """Brand name with fuzzy matching — Dave's STONE'S THROW vs Stone's Throw case."""
    norm_expected = _normalize_brand(expected)
    norm_text = _normalize_brand(extracted_text)

    if norm_expected in norm_text:
        return FieldCheck(
            field_name="Brand Name",
            expected=expected,
            found=expected,
            status=CheckStatus.PASS,
            message="Brand name matches.",
            confidence=1.0,
        )

    score = fuzz.token_set_ratio(norm_expected, norm_text)
    if score >= 80:
        return FieldCheck(
            field_name="Brand Name",
            expected=expected,
            found=f"(fuzzy match, {score:.0f}% similar)",
            status=CheckStatus.PASS,
            message=f"Brand name matches with minor formatting differences ({score:.0f}% similarity).",
            confidence=score / 100,
        )

    return FieldCheck(
        field_name="Brand Name",
        expected=expected,
        found="Not found on label",
        status=CheckStatus.FAIL,
        message=f"Brand name mismatch — expected '{expected}', not found on label.",
        confidence=score / 100,
    )


def _check_alcohol_content(expected: str, extracted_text: str) -> FieldCheck:
    """Compare ABV values numerically."""
    if not expected:
        return FieldCheck(
            field_name="Alcohol Content",
            expected="(not provided)",
            status=CheckStatus.SKIPPED,
            message="No alcohol content specified in application.",
        )

    expected_vals = _extract_abv_values(expected)
    found_vals = _extract_abv_values(extracted_text)

    if expected_vals and found_vals:
        if expected_vals & found_vals:
            matched = expected_vals & found_vals
            return FieldCheck(
                field_name="Alcohol Content",
                expected=expected,
                found=f"ABV {', '.join(sorted(matched))}%",
                status=CheckStatus.PASS,
                message="Alcohol content matches.",
                confidence=1.0,
            )
        return FieldCheck(
            field_name="Alcohol Content",
            expected=expected,
            found=f"Found: {', '.join(sorted(found_vals))}%",
            status=CheckStatus.FAIL,
            message="Alcohol content does not match application.",
            confidence=0.3,
        )

    found, _, score = _find_in_text(expected, extracted_text, fuzzy_threshold=90)
    if found:
        return FieldCheck(
            field_name="Alcohol Content",
            expected=expected,
            found=expected,
            status=CheckStatus.PASS,
            message="Alcohol content matches (text match).",
            confidence=score / 100,
        )

    return FieldCheck(
        field_name="Alcohol Content",
        expected=expected,
        found=f"Found: {found_vals or 'none detected'}",
        status=CheckStatus.FAIL,
        message="Alcohol content does not match application.",
        confidence=0.3,
    )


def _check_government_warning(expected: str, extracted_text: str) -> FieldCheck:
    """
    Government warning must be exact — Jenny's requirement.
    Checks for GOVERNMENT WARNING in all caps and full statement text.
    """
    warning_ref = expected.strip() if expected else STANDARD_GOVERNMENT_WARNING

    # Check header is ALL CAPS
    header_pattern = r"GOVERNMENT\s+WARNING\s*:"
    header_match = re.search(header_pattern, extracted_text)
    wrong_case = re.search(r"Government\s+Warning\s*:", extracted_text, re.IGNORECASE)
    if wrong_case and not header_match:
        return FieldCheck(
            field_name="Government Warning",
            expected="GOVERNMENT WARNING: (all caps, bold)",
            found=wrong_case.group(0),
            status=CheckStatus.FAIL,
            message="'Government Warning' must be 'GOVERNMENT WARNING:' in all caps.",
            confidence=0.0,
        )

    if not header_match:
        return FieldCheck(
            field_name="Government Warning",
            expected="GOVERNMENT WARNING: ...",
            found="Header not found",
            status=CheckStatus.FAIL,
            message="Government warning header not found on label.",
            confidence=0.0,
        )

    def collapse(s: str) -> str:
        return re.sub(r"\s+", " ", s.lower().strip())

    norm_ref = collapse(warning_ref)

    # Use first warning block only (OCR may duplicate bottom-crop text)
    idx = extracted_text.upper().find("GOVERNMENT WARNING")
    warning_on_label = extracted_text[idx:] if idx >= 0 else extracted_text
    second = warning_on_label.upper().find("GOVERNMENT WARNING", len("GOVERNMENT WARNING"))
    if second > 0:
        warning_on_label = warning_on_label[:second]
    norm_label_warning = collapse(warning_on_label)

    ratio = fuzz.ratio(norm_ref, norm_label_warning)
    token_ratio = fuzz.token_set_ratio(norm_ref, norm_label_warning)
    best = max(ratio, token_ratio)

    if best >= 90:
        return FieldCheck(
            field_name="Government Warning",
            expected="Standard TTB warning (exact)",
            found="Complete warning present",
            status=CheckStatus.PASS,
            message="Government warning statement matches (word-for-word).",
            confidence=best / 100,
        )

    if best >= 80:
        return FieldCheck(
            field_name="Government Warning",
            expected="Standard TTB warning (exact)",
            found="Warning present with minor differences",
            status=CheckStatus.WARNING,
            message=f"Warning text is {best:.0f}% similar — review for exact wording.",
            confidence=best / 100,
        )

    return FieldCheck(
        field_name="Government Warning",
        expected="Standard TTB warning (exact)",
        found="Incomplete or altered warning",
        status=CheckStatus.FAIL,
        message="Government warning does not match required text.",
        confidence=best / 100,
    )


def _check_generic_field(
    field_name: str,
    expected: str,
    extracted_text: str,
    fuzzy_threshold: int = 80,
) -> FieldCheck:
    """Generic fuzzy field check for class/type, net contents, etc."""
    if not expected:
        return FieldCheck(
            field_name=field_name,
            expected="(not provided)",
            status=CheckStatus.SKIPPED,
            message=f"No {field_name.lower()} specified in application.",
        )

    # Special handling for net contents — compare volumes
    if field_name == "Net Contents":
        expected_vol = _extract_volume(expected)
        found_vol = _extract_volume(extracted_text)
        if expected_vol and found_vol and expected_vol & found_vol:
            return FieldCheck(
                field_name=field_name,
                expected=expected,
                found=expected,
                status=CheckStatus.PASS,
                message=f"{field_name} matches.",
                confidence=1.0,
            )

    found, matched, score = _find_in_text(expected, extracted_text, fuzzy_threshold)
    if found:
        return FieldCheck(
            field_name=field_name,
            expected=expected,
            found=matched or expected,
            status=CheckStatus.PASS,
            message=f"{field_name} matches.",
            confidence=score / 100,
        )

    return FieldCheck(
        field_name=field_name,
        expected=expected,
        found="Not found on label",
        status=CheckStatus.FAIL,
        message=f"{field_name} not found or does not match.",
        confidence=score / 100,
    )


def verify_label(application: ApplicationData, extracted_text: str) -> list[FieldCheck]:
    """Run all field checks against extracted label text."""
    checks = [
        _check_brand_name(application.brand_name, extracted_text),
        _check_generic_field("Class/Type", application.class_type, extracted_text),
        _check_alcohol_content(application.alcohol_content, extracted_text),
        _check_generic_field("Net Contents", application.net_contents, extracted_text),
        _check_government_warning(application.government_warning, extracted_text),
    ]

    if application.bottler_producer:
        checks.append(
            _check_generic_field("Bottler/Producer", application.bottler_producer, extracted_text)
        )
    if application.country_of_origin:
        checks.append(
            _check_generic_field("Country of Origin", application.country_of_origin, extracted_text)
        )

    return checks


def overall_status(checks: list[FieldCheck]) -> CheckStatus:
    """Derive overall result from individual checks."""
    active = [c for c in checks if c.status != CheckStatus.SKIPPED]
    if any(c.status == CheckStatus.FAIL for c in active):
        return CheckStatus.FAIL
    if any(c.status == CheckStatus.WARNING for c in active):
        return CheckStatus.WARNING
    return CheckStatus.PASS
