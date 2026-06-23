"""
RecallRadar — Query Lambda
Serves recall data to the React dashboard via API Gateway.
"""

import json
import os
import logging
from decimal import Decimal
from collections import Counter
from urllib.parse import unquote

import boto3
from boto3.dynamodb.conditions import Key, Attr

from shared.analytics_utils import to_jsonable
from shared.state_coordinates import STATE_COORDINATES

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CLASSIFICATION_WEIGHTS = {
    "Class I": 3,
    "Class II": 2,
    "Class III": 1,
}

TABLE_NAME = os.environ.get("TABLE_NAME", "recallradar-recalls")
ANALYTICS_TABLE_NAME = os.environ.get("ANALYTICS_TABLE", "recallradar-analytics")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)
analytics_table = dynamodb.Table(ANALYTICS_TABLE_NAME)


class DecimalEncoder(json.JSONEncoder):
    """DynamoDB returns Decimal types — this converts them for JSON serialization."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def cors_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def get_recalls(params: dict) -> dict:
    """
    Paginated recall list with optional filters.

    Query params:
        classification  — "Class I", "Class II", "Class III"
        status          — "Ongoing", "Completed", "Terminated"
        state           — Two-letter state code (filters affected_states)
        from_date       — YYYYMMDD start date
        to_date         — YYYYMMDD end date
        limit           — Page size (default 25, max 100)
        next_token      — Pagination token from previous response
    """
    classification = params.get("classification")
    status = params.get("status")
    state = params.get("state")
    from_date = params.get("from_date")
    to_date = params.get("to_date")
    limit = min(int(params.get("limit", "25")), 100)
    next_token = params.get("next_token")

    if classification and not state:
        query_kwargs = {
            "IndexName": "classification-date-index",
            "KeyConditionExpression": Key("classification").eq(classification),
            "ScanIndexForward": False,
            "Limit": limit,
        }

        if from_date and to_date:
            query_kwargs["KeyConditionExpression"] &= Key("report_date").between(from_date, to_date)
        elif from_date:
            query_kwargs["KeyConditionExpression"] &= Key("report_date").gte(from_date)

        if status:
            query_kwargs["FilterExpression"] = Attr("status").eq(status)

        if next_token:
            query_kwargs["ExclusiveStartKey"] = json.loads(next_token)

        response = table.query(**query_kwargs)

    else:
        scan_kwargs = {"Limit": limit}
        filter_parts = []

        if classification:
            filter_parts.append(Attr("classification").eq(classification))
        if status:
            filter_parts.append(Attr("status").eq(status))
        if state:
            filter_parts.append(Attr("affected_states").contains(state))
        if from_date:
            filter_parts.append(Attr("report_date").gte(from_date))
        if to_date:
            filter_parts.append(Attr("report_date").lte(to_date))

        if filter_parts:
            combined = filter_parts[0]
            for part in filter_parts[1:]:
                combined = combined & part
            scan_kwargs["FilterExpression"] = combined

        if next_token:
            scan_kwargs["ExclusiveStartKey"] = json.loads(next_token)

        response = table.scan(**scan_kwargs)

    items = response.get("Items", [])
    result = {
        "recalls": items,
        "count": len(items),
    }

    if "LastEvaluatedKey" in response:
        result["next_token"] = json.dumps(response["LastEvaluatedKey"], cls=DecimalEncoder)

    return result


def get_recall_stats() -> dict:
    """
    Aggregated statistics across all recalls.
    Note: Scans entire table — in Phase 4, precompute these with Timestream.
    """
    items = []
    scan_kwargs = {
        "ProjectionExpression": "classification, #s, recalling_firm, affected_states, is_nationwide, report_date, ingested_at",
        "ExpressionAttributeNames": {"#s": "status"},
    }

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    classification_counts = Counter(item.get("classification", "Unknown") for item in items)
    status_counts = Counter(item.get("status", "Unknown") for item in items)
    firm_counts = Counter(item.get("recalling_firm", "Unknown") for item in items)
    firm_classification_counts = {}
    latest_ingested_at = None

    for item in items:
        firm_name = item.get("recalling_firm", "Unknown")
        classification = item.get("classification", "Unknown")
        ingested_at = item.get("ingested_at")

        if firm_name not in firm_classification_counts:
            firm_classification_counts[firm_name] = Counter()
        firm_classification_counts[firm_name][classification] += 1

        if ingested_at and (latest_ingested_at is None or ingested_at > latest_ingested_at):
            latest_ingested_at = ingested_at

    state_counts = Counter()
    state_classification_counts = {}
    for item in items:
        classification = item.get("classification", "Unknown")
        for st in item.get("affected_states", []):
            state_counts[st] += 1
            if st not in state_classification_counts:
                state_classification_counts[st] = Counter()
            state_classification_counts[st][classification] += 1

    nationwide_count = sum(1 for item in items if item.get("is_nationwide"))
    top_firms_by_severity = sorted(
        (
            {
                "firm": firm_name,
                "severity_score": sum(
                    count * CLASSIFICATION_WEIGHTS.get(classification, 0)
                    for classification, count in classifications.items()
                ),
                "total_recalls": sum(classifications.values()),
                "by_classification": dict(classifications),
            }
            for firm_name, classifications in firm_classification_counts.items()
        ),
        key=lambda firm: (firm["severity_score"], firm["total_recalls"], firm["firm"]),
        reverse=True,
    )[:10]

    return {
        "total_recalls": len(items),
        "by_classification": dict(classification_counts),
        "by_status": dict(status_counts),
        "top_firms": dict(firm_counts.most_common(10)),
        "top_firms_by_severity": top_firms_by_severity,
        "top_states": dict(state_counts.most_common(10)),
        "state_counts": dict(state_counts),
        "state_class_counts": {
            state: dict(classifications)
            for state, classifications in state_classification_counts.items()
        },
        "nationwide_count": nationwide_count,
        "nationwide_percentage": round(
            (nationwide_count / len(items) * 100) if items else 0, 1
        ),
        "state_coordinates": STATE_COORDINATES,
        "latest_ingested_at": latest_ingested_at,
    }


def get_recall_detail(recall_number: str) -> dict | None:
    """Fetch a single recall by recall_number (PK)."""
    response = table.query(
        KeyConditionExpression=Key("PK").eq(recall_number),
        Limit=1,
    )
    items = response.get("Items", [])
    if not items:
        return None
    return items[0]


def get_company_leaderboard(params: dict) -> dict:
    limit = min(int(params.get("limit", "20")), 100)
    profiles = _scan_analytics(
        FilterExpression=Attr("PK").begins_with("COMPANY#") & Attr("SK").eq("PROFILE")
    )

    for profile in profiles:
        _decode_json_fields(
            profile,
            ["recalls_by_source", "recalls_by_severity", "recalls_by_year", "hazard_counts"],
        )

    profiles.sort(key=lambda item: int(item.get("risk_score", 0)), reverse=True)
    return {"companies": profiles[:limit]}


def get_monthly_trends(params: dict) -> dict:
    months = min(int(params.get("months", "12")), 60)
    response = analytics_table.query(
        KeyConditionExpression=Key("PK").eq("TREND#MONTHLY"),
        ScanIndexForward=False,
        Limit=months,
    )
    items = [to_jsonable(item) for item in response.get("Items", [])]
    for item in items:
        _decode_json_fields(
            item,
            ["by_source", "by_category", "by_severity", "top_companies", "top_hazards"],
        )
    return {"monthly": sorted(items, key=lambda item: item["SK"])}


def get_seasonal_data(hazard: str) -> dict:
    decoded_hazard = unquote(hazard)
    response = analytics_table.query(
        KeyConditionExpression=Key("PK").eq(f"SEASONAL#{decoded_hazard}")
    )
    items = [to_jsonable(item) for item in response.get("Items", [])]
    for item in items:
        _decode_json_fields(item, ["year_counts"])
    return {"hazard_type": decoded_hazard, "seasonal": sorted(items, key=lambda item: item["SK"])}


def get_velocity_data(params: dict) -> dict:
    limit = min(int(params.get("limit", "48")), 100)
    items = _scan_analytics(FilterExpression=Attr("PK").begins_with("VELOCITY#"))
    items.sort(key=lambda item: (item.get("source", ""), item.get("quarter", "")), reverse=True)
    return {"velocity": items[:limit]}


def get_briefings(params: dict) -> dict:
    limit = min(int(params.get("limit", "12")), 52)
    response = analytics_table.query(
        KeyConditionExpression=Key("PK").eq("BRIEFING#WEEKLY"),
        ScanIndexForward=False,
        Limit=limit,
    )
    briefings = [to_jsonable(item) for item in response.get("Items", [])]
    return {"briefings": briefings}


def _scan_analytics(**kwargs) -> list:
    items = []
    response = analytics_table.scan(**kwargs)
    items.extend(to_jsonable(item) for item in response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = analytics_table.scan(
            **kwargs,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(to_jsonable(item) for item in response.get("Items", []))

    return items


def _decode_json_fields(item: dict, fields: list[str]) -> None:
    for field in fields:
        if isinstance(item.get(field), str):
            try:
                item[field] = json.loads(item[field])
            except (json.JSONDecodeError, TypeError):
                pass


def lambda_handler(event, context):
    """Routes API Gateway requests to the appropriate handler."""
    logger.info(f"Received event: {json.dumps(event)}")

    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/")
    params = event.get("queryStringParameters") or {}
    path_params = event.get("pathParameters") or {}

    if http_method == "OPTIONS":
        return cors_response(200, {"message": "OK"})

    try:
        if path == "/recalls/stats":
            result = get_recall_stats()
            return cors_response(200, result)

        elif path == "/analytics/companies":
            result = get_company_leaderboard(params)
            return cors_response(200, result)

        elif path == "/analytics/trends":
            result = get_monthly_trends(params)
            return cors_response(200, result)

        elif path.startswith("/analytics/seasonal/"):
            hazard = path_params.get("hazard") or path.rsplit("/", 1)[-1]
            result = get_seasonal_data(hazard)
            return cors_response(200, result)

        elif path == "/analytics/velocity":
            result = get_velocity_data(params)
            return cors_response(200, result)

        elif path == "/analytics/briefings":
            result = get_briefings(params)
            return cors_response(200, result)

        elif path.startswith("/recalls/") and path_params.get("recall_number"):
            recall = get_recall_detail(path_params["recall_number"])
            if recall is None:
                return cors_response(404, {"error": "Recall not found"})
            return cors_response(200, recall)

        elif path == "/recalls":
            result = get_recalls(params)
            return cors_response(200, result)

        else:
            return cors_response(404, {"error": "Not found"})

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return cors_response(500, {"error": "Internal server error"})
