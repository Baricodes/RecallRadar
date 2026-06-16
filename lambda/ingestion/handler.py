"""
RecallRadar — FDA Food Recall Ingestion Lambda
Fetches recent food enforcement reports from openFDA and persists to DynamoDB.
Idempotent: safe to run on any schedule without creating duplicates.
"""

import json
import os
import re
import logging
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

TABLE_NAME = os.environ.get("TABLE_NAME", "recallradar-recalls")
OPENFDA_BASE = "https://api.fda.gov/food/enforcement.json"
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "90"))
PAGE_SIZE = 100  # openFDA max is 1000, but 100 is safer for Lambda memory

# US state abbreviations for parsing distribution_pattern
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "GU", "VI", "AS", "MP"
}

# Full state name → abbreviation mapping for distribution_pattern parsing
STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC", "puerto rico": "PR"
}


# ──────────────────────────────────────────────
# State Parsing Logic
# ──────────────────────────────────────────────

def parse_distribution_pattern(pattern: str) -> dict:
    """
    Parses the openFDA distribution_pattern field into structured state data.

    The distribution_pattern field is free text with inconsistent formatting.
    Examples:
        "Nationwide"
        "FL, MI, MS, and OH."
        "State of California"
        "NY, NJ, CT, PA, and online sales nationwide"
        "Distributed in TX and LA through retail stores"

    Returns:
        {
            "affected_states": ["FL", "MI", "MS", "OH"],
            "is_nationwide": False
        }
    """
    if not pattern:
        return {"affected_states": [], "is_nationwide": False}

    pattern_lower = pattern.lower().strip()

    # Check for nationwide distribution
    nationwide_signals = ["nationwide", "national distribution", "all states",
                          "united states", "throughout the us", "all 50 states"]
    is_nationwide = any(signal in pattern_lower for signal in nationwide_signals)

    affected_states = set()

    if is_nationwide:
        affected_states = set(US_STATES) - {"PR", "GU", "VI", "AS", "MP"}
    else:
        # Strategy 1: Find two-letter state abbreviations
        abbrev_matches = re.findall(r'\b([A-Z]{2})\b', pattern)
        for match in abbrev_matches:
            if match in US_STATES:
                affected_states.add(match)

        # Strategy 2: Find full state names
        for name, abbrev in STATE_NAMES.items():
            if name in pattern_lower:
                affected_states.add(abbrev)

    return {
        "affected_states": sorted(list(affected_states)),
        "is_nationwide": is_nationwide
    }


# ──────────────────────────────────────────────
# openFDA API Client
# ──────────────────────────────────────────────

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


# ──────────────────────────────────────────────
# DynamoDB Writer
# ──────────────────────────────────────────────

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
                "ingested_at": datetime.now(timezone.utc).isoformat()
            }

            # DynamoDB doesn't allow empty strings — clean them
            item = {k: v for k, v in item.items() if v != "" and v != []}

            batch.put_item(Item=item)
            written += 1

    return written


# ──────────────────────────────────────────────
# Lambda Handler
# ──────────────────────────────────────────────

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

        # openFDA caps skip at 26000
        if skip >= min(total_available, 26000):
            break

    logger.info(f"Ingestion complete — {total_written} total records written")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Ingestion complete",
            "records_written": total_written,
            "lookback_days": LOOKBACK_DAYS,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    }
