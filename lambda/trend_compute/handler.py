"""Weekly Phase 4 trend computation Lambda."""

import json
import logging
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

import boto3

from shared.analytics_utils import (
    category_name,
    company_name,
    hazard_type,
    normalize_company,
    recall_date,
    recall_month,
    risk_score,
    source_name,
    to_dynamodb_item,
    to_jsonable,
    trend_direction,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
recalls_table = dynamodb.Table(os.environ["RECALLS_TABLE"])
analytics_table = dynamodb.Table(os.environ["ANALYTICS_TABLE"])


def lambda_handler(event, context):
    logger.info("Starting weekly trend computation")
    recalls = _scan_all_recalls()
    logger.info("Scanned %s recall records", len(recalls))

    monthly = _compute_monthly_snapshots(recalls)
    seasonal = _compute_seasonal_baselines(recalls)
    velocity = _compute_resolution_velocity(recalls)
    companies = _compute_company_profiles(recalls)
    anomalies = _detect_anomalies(monthly, seasonal)

    _batch_write_analytics(monthly + seasonal + velocity + companies)

    return {
        "status": "SUCCESS",
        "total_recalls_scanned": len(recalls),
        "monthly_snapshots": len(monthly),
        "seasonal_baselines": len(seasonal),
        "velocity_records": len(velocity),
        "company_profiles": len(companies),
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies[:10],
    }


def _scan_all_recalls() -> list:
    items = []
    kwargs = {}
    while True:
        response = recalls_table.scan(**kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    return [to_jsonable(item) for item in items]


def _compute_monthly_snapshots(recalls: list) -> list:
    months = defaultdict(
        lambda: {
            "total": 0,
            "by_source": Counter(),
            "by_category": Counter(),
            "by_severity": Counter(),
            "companies": Counter(),
            "hazards": Counter(),
        }
    )

    for recall in recalls:
        year_month = recall_month(recall)
        if not year_month:
            continue

        data = months[year_month]
        data["total"] += 1
        data["by_source"][source_name(recall)] += 1
        data["by_category"][category_name(recall)] += 1
        data["by_severity"][recall.get("classification", "Unknown")] += 1
        data["companies"][company_name(recall)] += 1
        data["hazards"][hazard_type(recall)] += 1

    items = []
    for year_month, data in sorted(months.items()):
        items.append(
            {
                "PK": "TREND#MONTHLY",
                "SK": year_month,
                "total_recalls": data["total"],
                "by_source": json.dumps(dict(data["by_source"])),
                "by_category": json.dumps(dict(data["by_category"])),
                "by_severity": json.dumps(dict(data["by_severity"])),
                "top_companies": json.dumps(_top_entries(data["companies"], "name")),
                "top_hazards": json.dumps(_top_entries(data["hazards"], "type")),
                "updated_at": _now(),
            }
        )
    return items


def _compute_seasonal_baselines(recalls: list) -> list:
    seasonal = defaultdict(lambda: defaultdict(Counter))

    for recall in recalls:
        date = recall_date(recall)
        if len(date) < 7:
            continue
        seasonal[hazard_type(recall)][date[5:7]][date[:4]] += 1

    items = []
    for hazard, months in seasonal.items():
        for month, year_counts in months.items():
            counts = list(year_counts.values())
            avg = sum(counts) / len(counts) if counts else 0
            std_dev = (
                math.sqrt(sum((count - avg) ** 2 for count in counts) / len(counts))
                if len(counts) > 1
                else 0
            )
            items.append(
                {
                    "PK": f"SEASONAL#{hazard}",
                    "SK": f"MONTH#{month}",
                    "hazard_type": hazard,
                    "month": month,
                    "avg_count": round(avg, 2),
                    "std_dev": round(std_dev, 2),
                    "year_counts": json.dumps(dict(year_counts)),
                    "years_of_data": len(counts),
                    "updated_at": _now(),
                }
            )
    return items


def _compute_resolution_velocity(recalls: list) -> list:
    velocity = defaultdict(lambda: {"days_to_close": [], "open": 0, "closed": 0})

    for recall in recalls:
        date = recall_date(recall)
        if len(date) < 7:
            continue

        quarter = _quarter_for_date(date)
        source = source_name(recall)
        status = str(recall.get("status", "")).lower()
        bucket = velocity[(source, quarter)]

        if status in {"completed", "terminated", "closed"}:
            bucket["closed"] += 1
            days = _days_to_close(recall, date)
            if days is not None:
                bucket["days_to_close"].append(days)
        else:
            bucket["open"] += 1

    items = []
    for (source, quarter), data in velocity.items():
        days = sorted(data["days_to_close"])
        closed = data["closed"]
        items.append(
            {
                "PK": f"VELOCITY#{source}",
                "SK": quarter,
                "source": source,
                "quarter": quarter,
                "avg_days_to_close": round(sum(days) / len(days), 1) if days else 0,
                "median_days_to_close": round(days[len(days) // 2], 1) if days else 0,
                "total_closed": closed,
                "total_open": data["open"],
                "pct_closed_within_30": _pct_within(days, 30),
                "pct_closed_within_90": _pct_within(days, 90),
                "updated_at": _now(),
            }
        )
    return items


def _compute_company_profiles(recalls: list) -> list:
    companies = defaultdict(
        lambda: {
            "display": "",
            "total": 0,
            "by_source": Counter(),
            "by_severity": Counter(),
            "by_year": Counter(),
            "hazards": Counter(),
            "first_date": "",
            "latest_date": "",
        }
    )

    for recall in recalls:
        display = company_name(recall)
        if display == "Unknown":
            continue
        key = normalize_company(display)
        date = recall_date(recall)
        year = date[:4] if len(date) >= 4 else str(datetime.now(timezone.utc).year)
        data = companies[key]
        data["display"] = data["display"] or display
        data["total"] += 1
        data["by_source"][source_name(recall)] += 1
        data["by_severity"][recall.get("classification", "Unknown")] += 1
        data["by_year"][year] += 1
        data["hazards"][hazard_type(recall)] += 1
        if date:
            data["first_date"] = min(data["first_date"], date) if data["first_date"] else date
            data["latest_date"] = max(data["latest_date"], date)

    items = []
    for company_key, data in companies.items():
        trend = trend_direction(dict(data["by_year"]))
        items.append(
            {
                "PK": f"COMPANY#{company_key}",
                "SK": "PROFILE",
                "company_name": data["display"],
                "company_key": company_key,
                "total_recalls": data["total"],
                "recalls_by_source": json.dumps(dict(data["by_source"])),
                "recalls_by_severity": json.dumps(dict(data["by_severity"])),
                "recalls_by_year": json.dumps(dict(data["by_year"])),
                "hazard_counts": json.dumps(dict(data["hazards"])),
                "most_common_hazard": data["hazards"].most_common(1)[0][0],
                "most_recent_recall_date": data["latest_date"],
                "first_recall_date": data["first_date"],
                "avg_recalls_per_year": round(data["total"] / max(len(data["by_year"]), 1), 2),
                "trend_direction": trend,
                "risk_score": risk_score(data["total"], dict(data["by_severity"]), trend),
                "updated_at": _now(),
            }
        )
    return items


def _detect_anomalies(monthly_items: list, seasonal_items: list) -> list:
    baselines = {}
    for item in seasonal_items:
        baselines.setdefault(item["hazard_type"], {})[item["month"]] = (
            item["avg_count"],
            item["std_dev"],
        )

    current_ym = datetime.now(timezone.utc).strftime("%Y-%m")
    current_month = current_ym[5:7]
    current = next((item for item in monthly_items if item["SK"] == current_ym), None)
    if not current:
        return []

    anomalies = []
    for hazard_entry in json.loads(current.get("top_hazards", "[]")):
        hazard = hazard_entry["type"]
        count = hazard_entry["count"]
        baseline = baselines.get(hazard, {}).get(current_month)
        if not baseline:
            continue

        avg, std = baseline
        if std > 0 and count > avg + (2 * std):
            anomalies.append(
                {
                    "hazard_type": hazard,
                    "current_count": count,
                    "baseline_avg": round(avg, 1),
                    "baseline_std": round(std, 1),
                    "z_score": round((count - avg) / std, 2),
                    "month": current_ym,
                }
            )

    return sorted(anomalies, key=lambda item: item["z_score"], reverse=True)


def _batch_write_analytics(items: list) -> None:
    with analytics_table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=to_dynamodb_item(item))


def _top_entries(counter: Counter, key_name: str, limit: int = 5) -> list:
    return [{key_name: name, "count": count} for name, count in counter.most_common(limit)]


def _quarter_for_date(date: str) -> str:
    month = int(date[5:7])
    return f"{date[:4]}-Q{((month - 1) // 3) + 1}"


def _days_to_close(recall: dict, normalized_recall_date: str) -> int | None:
    metadata = recall.get("source_metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}

    closed_date = (
        recall.get("closed_date")
        or recall.get("termination_date")
        or metadata.get("closed_date")
        or metadata.get("field_closed_date")
    )
    closed = _parse_date(closed_date)
    opened = _parse_date(normalized_recall_date)
    if not closed or not opened:
        return None

    days = (closed - opened).days
    return days if 0 <= days <= 365 else None


def _parse_date(value: str | None):
    normalized = recall_date({"recall_date": value})
    if len(normalized) < 10:
        return None
    try:
        return datetime.strptime(normalized[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _pct_within(days: list, threshold: int) -> float:
    return round((len([day for day in days if day <= threshold]) / len(days) * 100), 1) if days else 0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
