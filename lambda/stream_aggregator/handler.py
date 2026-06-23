"""DynamoDB Streams aggregator for Phase 4 company risk profiles."""

import json
import logging
import os
from collections import Counter
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.types import TypeDeserializer

from shared.analytics_utils import (
    company_name,
    hazard_type,
    normalize_company,
    recall_date,
    risk_score,
    source_name,
    trend_direction,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
analytics_table = dynamodb.Table(os.environ["ANALYTICS_TABLE"])
deserializer = TypeDeserializer()


def lambda_handler(event, context):
    processed = 0
    skipped = 0

    for record in event.get("Records", []):
        if record.get("eventName") != "INSERT":
            skipped += 1
            continue

        image = record.get("dynamodb", {}).get("NewImage")
        if not image:
            skipped += 1
            continue

        recall = _deserialize_image(image)
        company = company_name(recall)
        if not company or company == "Unknown":
            skipped += 1
            continue

        try:
            _update_company_profile(recall, company)
            processed += 1
        except Exception as exc:
            logger.error("Failed to update company profile for %s: %s", company, exc, exc_info=True)

    return {"status": "OK", "processed": processed, "skipped": skipped}


def _deserialize_image(image: dict) -> dict:
    return {key: deserializer.deserialize(value) for key, value in image.items()}


def _update_company_profile(recall: dict, display_company: str) -> None:
    company_key = normalize_company(display_company)
    source = source_name(recall)
    severity = recall.get("classification", "Unknown")
    date = recall_date(recall)
    year = date[:4] if len(date) >= 4 else str(datetime.now(timezone.utc).year)
    hazard = hazard_type(recall)
    now = datetime.now(timezone.utc).isoformat()

    key = {"PK": f"COMPANY#{company_key}", "SK": "PROFILE"}
    existing = analytics_table.get_item(Key=key).get("Item", {})

    recalls_by_source = _decode_counter(existing.get("recalls_by_source"))
    recalls_by_source[source] += 1

    recalls_by_severity = _decode_counter(existing.get("recalls_by_severity"))
    recalls_by_severity[severity] += 1

    recalls_by_year = _decode_counter(existing.get("recalls_by_year"))
    recalls_by_year[year] += 1

    hazards = _decode_counter(existing.get("hazard_counts"))
    hazards[hazard] += 1

    total_recalls = int(existing.get("total_recalls", 0)) + 1
    first_recall_date = existing.get("first_recall_date") or date
    most_recent_recall_date = max(existing.get("most_recent_recall_date", ""), date)
    trend = trend_direction(dict(recalls_by_year))

    analytics_table.put_item(
        Item={
            "PK": key["PK"],
            "SK": key["SK"],
            "company_name": existing.get("company_name") or display_company,
            "company_key": company_key,
            "total_recalls": total_recalls,
            "recalls_by_source": json.dumps(dict(recalls_by_source)),
            "recalls_by_severity": json.dumps(dict(recalls_by_severity)),
            "recalls_by_year": json.dumps(dict(recalls_by_year)),
            "hazard_counts": json.dumps(dict(hazards)),
            "most_common_hazard": hazards.most_common(1)[0][0],
            "most_recent_recall_date": most_recent_recall_date,
            "first_recall_date": min(first_recall_date, date) if date else first_recall_date,
            "avg_recalls_per_year": round(total_recalls / max(len(recalls_by_year), 1), 2),
            "trend_direction": trend,
            "risk_score": risk_score(total_recalls, dict(recalls_by_severity), trend),
            "updated_at": now,
        }
    )


def _decode_counter(value) -> Counter:
    if isinstance(value, str):
        try:
            return Counter(json.loads(value))
        except json.JSONDecodeError:
            return Counter()
    if isinstance(value, dict):
        return Counter(value)
    return Counter()
