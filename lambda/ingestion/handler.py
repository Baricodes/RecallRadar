"""
RecallRadar — FDA Food Recall Ingestion Lambda
Fetches recent food enforcement reports from openFDA and persists to DynamoDB.
Idempotent: safe to run on any schedule without creating duplicates.
"""

import json
import os
import logging
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

import boto3

from shared.state_parsing import parse_distribution_pattern

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("TABLE_NAME", "recallradar-recalls")
OPENFDA_BASE = "https://api.fda.gov/food/enforcement.json"
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "90"))
PAGE_SIZE = 100


def fetch_recalls(skip: int = 0) -> dict:
    """Fetch a page of recall records from openFDA."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    lookback = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d")

    url = (
        f"{OPENFDA_BASE}"
        f"?search=report_date:[{lookback}+TO+{today}]"
        f"&limit={PAGE_SIZE}"
        f"&skip={skip}"
    )

    logger.info(f"Fetching openFDA: skip={skip}")

    req = Request(url, headers={"User-Agent": "RecallRadar/1.0"})
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        logger.error(f"openFDA HTTP error: {e.code} — {e.reason}")
        raise
    except URLError as e:
        logger.error(f"openFDA connection error: {e.reason}")
        raise


def write_recalls_to_dynamo(recalls: list, table) -> int:
    """
    Batch-write recall records to DynamoDB.
    Uses batch_writer for efficiency (auto-batches into 25-item writes).
    Returns count of records written.
    """
    written = 0

    with table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
        for recall in recalls:
            recall_number = recall.get("recall_number")
            if not recall_number:
                logger.warning("Skipping recall with no recall_number")
                continue

            report_date = recall.get("report_date", "00000000")
            source = "FDA"

            dist_data = parse_distribution_pattern(
                recall.get("distribution_pattern", "")
            )

            item = {
                "PK": recall_number,
                "SK": f"{source}#{report_date}",
                "classification": recall.get("classification", "Unknown"),
                "status": recall.get("status", "Unknown"),
                "report_date": report_date,
                "recall_initiation_date": recall.get("recall_initiation_date", ""),
                "recalling_firm": recall.get("recalling_firm", "Unknown"),
                "product_description": recall.get("product_description", ""),
                "reason_for_recall": recall.get("reason_for_recall", ""),
                "distribution_pattern": recall.get("distribution_pattern", ""),
                "affected_states": dist_data["affected_states"],
                "is_nationwide": dist_data["is_nationwide"],
                "firm_city": recall.get("city", ""),
                "firm_state": recall.get("state", ""),
                "country": recall.get("country", ""),
                "product_quantity": recall.get("product_quantity", ""),
                "voluntary_mandated": recall.get("voluntary_mandated", ""),
                "code_info": recall.get("code_info", ""),
                "source": source,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }

            item = {k: v for k, v in item.items() if v != "" and v != []}

            batch.put_item(Item=item)
            written += 1

    return written


def lambda_handler(event, context):
    """
    Entry point. Paginates through openFDA API and writes all
    recent recalls to DynamoDB.
    """
    logger.info(f"RecallRadar ingestion starting — lookback={LOOKBACK_DAYS} days")

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    total_written = 0
    skip = 0
    total_available = None

    while True:
        try:
            data = fetch_recalls(skip=skip)
        except Exception as e:
            logger.error(f"Failed to fetch page at skip={skip}: {e}")
            break

        results = data.get("results", [])
        if not results:
            logger.info(f"No results at skip={skip}, stopping pagination")
            break

        if total_available is None:
            total_available = data.get("meta", {}).get("results", {}).get("total", 0)
            logger.info(f"Total records available from openFDA: {total_available}")

        written = write_recalls_to_dynamo(results, table)
        total_written += written
        skip += PAGE_SIZE

        logger.info(f"Page written: {written} records (total so far: {total_written})")

        if skip >= min(total_available, 26000):
            break

    logger.info(f"Ingestion complete — {total_written} total records written")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Ingestion complete",
            "records_written": total_written,
            "lookback_days": LOOKBACK_DAYS,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }),
    }
