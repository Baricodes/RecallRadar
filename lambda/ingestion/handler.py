"""RecallRadar multi-source ingestion Lambda."""

import json
import logging
import os
from datetime import datetime, timedelta, timezone

import boto3

from shared.adapters import ADAPTERS

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("TABLE_NAME", "recallradar-recalls")
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "90"))
DEFAULT_SOURCE_NAME = os.environ.get("SOURCE_NAME", "ALL")
METRIC_NAMESPACE = "RecallRadar"


def publish_source_metric(source: str, metric_name: str, count: int) -> None:
    if count <= 0:
        return

    cloudwatch = boto3.client("cloudwatch")
    cloudwatch.put_metric_data(
        Namespace=METRIC_NAMESPACE,
        MetricData=[
            {
                "MetricName": metric_name,
                "Value": count,
                "Unit": "Count",
                "Dimensions": [
                    {
                        "Name": "Source",
                        "Value": source,
                    }
                ],
            }
        ],
    )


def write_records_to_dynamo(source: str, records: list, table) -> dict:
    written = 0
    failed_recall_ids = []

    with table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
        for record in records:
            try:
                batch.put_item(Item=record.to_dynamodb_item())
                written += 1
            except Exception as e:
                failed_recall_ids.append(record.recall_id)
                logger.error("Failed to write recall_id=%s: %s", record.recall_id, e, exc_info=True)

    publish_source_metric(source, "RecordsWritten", written)

    return {
        "source": source,
        "fetched": len(records),
        "written": written,
        "failed": len(failed_recall_ids),
        "failed_recall_ids": failed_recall_ids,
    }


def resolve_sources(event: dict) -> list:
    requested = event.get("sources") or event.get("source") or DEFAULT_SOURCE_NAME
    if requested in (None, "", "ALL"):
        return list(ADAPTERS.keys())
    if isinstance(requested, str):
        return [requested]
    return requested


def lambda_handler(event, context):
    event = event or {}
    limit = int(event.get("limit", os.environ.get("INGESTION_LIMIT", "100")))
    since_date = event.get("since_date") or (
        datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    ).strftime("%Y-%m-%d")
    sources = resolve_sources(event)

    logger.info(
        "RecallRadar ingestion starting sources=%s since_date=%s limit=%s",
        sources,
        since_date,
        limit,
    )

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    results = []
    for source in sources:
        adapter_cls = ADAPTERS.get(source)
        if not adapter_cls:
            logger.warning("Unsupported source requested: %s", source)
            results.append({"source": source, "status": "SKIPPED", "error": "Unsupported source"})
            continue

        adapter = adapter_cls()
        records = adapter.ingest(since_date=since_date, limit=limit)
        write_result = write_records_to_dynamo(source, records, table)
        write_result["status"] = "SUCCESS"
        results.append(write_result)

    total_written = sum(result.get("written", 0) for result in results)
    total_failed = sum(result.get("failed", 0) for result in results)
    response = {
        "message": "Ingestion complete",
        "sources": results,
        "records_written": total_written,
        "records_failed": total_failed,
        "since_date": since_date,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("Ingestion complete: %s", json.dumps(response))
    return response
