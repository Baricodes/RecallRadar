"""Helpers shared by Phase 4 analytics Lambdas."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal


UNKNOWN = "Unknown"


def normalize_date(value: str | None) -> str:
    """Return a YYYY-MM-DD date where possible, preserving sortable unknowns."""
    if not value:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", text):
        return text[:10]

    for fmt in ("%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return text[:10]


def recall_date(record: dict) -> str:
    return normalize_date(
        record.get("recall_date")
        or record.get("recall_initiation_date")
        or record.get("report_date")
        or record.get("ingested_at")
    )


def recall_month(record: dict) -> str:
    date = recall_date(record)
    return date[:7] if len(date) >= 7 else ""


def company_name(record: dict) -> str:
    return (
        record.get("company")
        or record.get("recalling_firm")
        or record.get("manufacturer")
        or UNKNOWN
    )


def source_name(record: dict) -> str:
    return record.get("source") or UNKNOWN


def category_name(record: dict) -> str:
    return record.get("category") or record.get("product_type") or "Food"


def hazard_type(record: dict) -> str:
    explicit = record.get("hazard_type") or record.get("hazard")
    if explicit:
        return str(explicit)

    reason = (record.get("reason_for_recall") or "").lower()
    hazard_map = [
        ("allergen", "Allergen"),
        ("undeclared", "Undeclared Allergen"),
        ("listeria", "Listeria"),
        ("salmonella", "Salmonella"),
        ("e. coli", "E. coli"),
        ("ecoli", "E. coli"),
        ("foreign", "Foreign Material"),
        ("metal", "Foreign Material"),
        ("plastic", "Foreign Material"),
        ("label", "Labeling"),
        ("misbrand", "Misbranding"),
        ("contamination", "Contamination"),
    ]
    for needle, label in hazard_map:
        if needle in reason:
            return label
    return "Other"


def normalize_company(name: str) -> str:
    """Normalize company names for grouping while keeping display names separate."""
    normalized = str(name or "").strip().upper()
    normalized = re.sub(r"[,.]", "", normalized)
    normalized = re.sub(r"\b(INC|LLC|CORP|CORPORATION|CO|COMPANY|LTD)\b", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or UNKNOWN.upper()


def trend_direction(by_year: dict) -> str:
    if len(by_year) < 2:
        return "insufficient_data"

    sorted_years = sorted(by_year.keys())
    current_count = int(by_year[sorted_years[-1]])
    prior_counts = [int(by_year[year]) for year in sorted_years[:-1]]
    prior_avg = sum(prior_counts) / len(prior_counts)

    if prior_avg == 0:
        return "increasing" if current_count > 0 else "stable"

    ratio = current_count / prior_avg
    if ratio > 1.3:
        return "increasing"
    if ratio < 0.7:
        return "decreasing"
    return "stable"


def risk_score(total: int, by_severity: dict, trend: str) -> int:
    import math

    volume_score = min(40, int(math.log2(max(total, 1) + 1) * 8))
    class_1 = int(by_severity.get("Class I", 0))
    class_2 = int(by_severity.get("Class II", 0))
    severity_score = min(40, (class_1 * 15) + (class_2 * 5))
    trend_score = {"increasing": 20, "stable": 10, "decreasing": 0}.get(trend, 5)
    return min(100, volume_score + severity_score + trend_score)


def to_jsonable(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value
