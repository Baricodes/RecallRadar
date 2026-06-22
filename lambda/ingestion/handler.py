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
METRIC_NAMESPACE = "RecallRadar"


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


def publish_parse_failure_metric(count: int) -> None:
    """Publish custom CloudWatch metric for distribution_pattern parse failures."""
    if count <= 0:
        return

    cloudwatch = boto3.client("cloudwatch")
    cloudwatch.put_metric_data(
        Namespace=METRIC_NAMESPACE,
        MetricData=[
            {
                "MetricName": "ParseFailures",
                "Value": count,
                "Unit": "Count",
                "Dimensions": [
                    {
                        "Name": "FunctionName",
                        "Value": os.environ.get(
                            "AWS_LAMBDA_FUNCTION_NAME", "recallradar-ingestion"
                        ),
                    }
                ],
            }
        ],
    )


def write_recalls_to_dynamo(recalls: list, table) -> dict:
    """
    Batch-write recall records to DynamoDB.
    Catches individual record failures without aborting the batch.
    Returns summary counts for logging and metrics.
    """
    written = 0
    failed_recall_numbers = []
    parse_failures = 0

    with table.batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
        for recall in recalls:
            recall_number = recall.get("recall_number")
            if not recall_number:
                logger.warning("Skipping recall with no recall_number")
                continue

            try:
                report_date = recall.get("report_date", "00000000")
                source = "FDA"

                try:
                    dist_data = parse_distribution_pattern(
                        recall.get("distribution_pattern", "")
                    )
                except Exception as e:
                    parse_failures += 1
                    logger.warning(
                        f"Parse failure for recall_number={recall_number}: {e}"
                    )
                    dist_data = {"affected_states": [], "is_nationwide": False}

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

            except Exception as e:
                failed_recall_numbers.append(recall_number)
                logger.error(
                    f"Failed to write recall_number={recall_number}: {e}",
                    exc_info=True,
                )

    if failed_recall_numbers:
        logger.error(
            f"Failed recall_numbers for manual investigation: {failed_recall_numbers}"
        )

    publish_parse_failure_metric(parse_failures)

    return {
        "written": written,
        "failed_recall_numbers": failed_recall_numbers,
        "parse_failures": parse_failures,
    }


def lambda_handler(event, context):
    """
    Entry point. Paginates through openFDA API and writes all
    recent recalls to DynamoDB.
    """
    logger.info(f"RecallRadar ingestion starting — lookback={LOOKBACK_DAYS} days")

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    total_written = 0
    total_failed = 0
    total_parse_failures = 0
    all_failed_recall_numbers = []
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

        page_result = write_recalls_to_dynamo(results, table)
        total_written += page_result["written"]
        total_failed += len(page_result["failed_recall_numbers"])
        total_parse_failures += page_result["parse_failures"]
        all_failed_recall_numbers.extend(page_result["failed_recall_numbers"])
        skip += PAGE_SIZE

        logger.info(
            f"Page written: {page_result['written']} records "
            f"(total so far: {total_written}, failed: {total_failed})"
        )

        if skip >= min(total_available, 26000):
            break

    logger.info(
        f"Ingestion complete — {total_written} written, "
        f"{total_failed} failed, {total_parse_failures} parse failures"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Ingestion complete",
            "records_written": total_written,
            "records_failed": total_failed,
            "parse_failures": total_parse_failures,
            "failed_recall_numbers": all_failed_recall_numbers,
            "lookback_days": LOOKBACK_DAYS,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }),
    }
