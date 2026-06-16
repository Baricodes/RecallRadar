# RecallRadar — Phase 1 MVP Build Guide

> A real-time recall intelligence dashboard that aggregates FDA, CPSC, and NHTSA data, maps geographic impact, and (in later phases) uses AI to score what you should actually worry about.

---

## Table of Contents

1. [Project Overview & Portfolio Positioning](#1-project-overview--portfolio-positioning)
2. [Architecture](#2-architecture)
3. [Data Sources (Verified Live)](#3-data-sources-verified-live)
4. [Phase 1A — DynamoDB Table Design](#phase-1a--dynamodb-table-design)
5. [Phase 1B — Ingestion Lambda](#phase-1b--ingestion-lambda)
6. [Phase 1C — State Parsing & Geocoding](#phase-1c--state-parsing--geocoding)
7. [Phase 1D — EventBridge Scheduler](#phase-1d--eventbridge-scheduler)
8. [Phase 1E — Query Lambda + API Gateway](#phase-1e--query-lambda--api-gateway)
9. [Phase 1F — React Dashboard](#phase-1f--react-dashboard)
10. [Phase 1G — S3 + CloudFront Hosting](#phase-1g--s3--cloudfront-hosting)
11. [Phase 1H — Monitoring & Hardening](#phase-1h--monitoring--hardening)
12. [Phase 1I — Documentation & Portfolio](#phase-1i--documentation--portfolio)
13. [Extension Roadmap (Phases 2–7)](#extension-roadmap-phases-27)

---

## 1. Project Overview & Portfolio Positioning

### What it is (recruiter-readable)

RecallRadar is a real-time recall intelligence platform that ingests product recall data from federal agencies (FDA, CPSC, NHTSA), maps geographic impact across the United States, and surfaces insights about recall severity, frequency, and trends — data that exists publicly but nobody aggregates or visualizes in one place.

### Why it matters for your portfolio

This project fills three gaps your current portfolio doesn't cover:

| Gap | How RecallRadar fills it |
|---|---|
| **No streaming/long-running projects** | RecallRadar runs continuously — EventBridge triggers ingestion on a schedule, data accumulates over weeks and months, and the dashboard reflects live state. Every other project in your portfolio is trigger-and-done. |
| **No frontend/visualization** | A React dashboard with an interactive US map, live feed, and analytics charts. This is the first project a reviewer can *see running*. |
| **No CloudFront/S3 static hosting** | Adds CDN, static hosting, and CORS configuration to your service portfolio. |

### What new AWS services this adds

Services you haven't used in any prior project:
- **CloudFront** — CDN for the React dashboard
- **S3 (static hosting)** — Hosts the built React app
- **EventBridge Scheduler** — Cron-based Lambda triggers (you've used EventBridge rules, but Scheduler is the newer, more granular service)

Services you've used before that deepen here:
- **DynamoDB** — More complex access patterns (GSIs, pagination, filtering)
- **Lambda** — Multiple functions with shared layers
- **API Gateway** — REST API with CORS, query parameters, pagination
- **IAM** — Cross-service least privilege
- **CloudWatch** — Dashboard and alarms for a long-running system

### How it connects to your security narrative

The architecture pattern — **ingest → normalize → classify → store → alert → visualize** — is identical to a Security Operations Center (SOC) dashboard. A hiring manager at Booz Allen sees this and recognizes the pattern immediately: swap "food recalls" for "security findings" and the architecture is the same. The skill transfer is obvious without you having to spell it out.

### The McBroken angle

The FDA, CPSC, and NHTSA all publish recall data through free public APIs — but nobody aggregates them in real-time, maps the geographic impact, or answers questions like "which company has the most recalls this year?" or "what percentage of recalls in my state are Class I?" RecallRadar does. The data is public. The insight is not.

---

## 2. Architecture

### Phase 1 MVP Architecture

```
EventBridge Scheduler (every 6 hours)
        │
        ▼
┌─────────────────────────┐
│  Ingestion Lambda       │──────▶ openFDA API
│  (Python 3.12)          │       (food/enforcement)
│                         │
│  • Fetches new recalls  │
│  • Parses states from   │
│    distribution_pattern │
│  • Deduplicates by      │
│    recall_number        │
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│  DynamoDB               │
│  recallradar-recalls    │
│                         │
│  PK: recall_number      │
│  GSI1: classification   │
│  GSI2: report_date      │
└─────────────────────────┘
        ▲
        │
┌─────────────────────────┐
│  Query Lambda           │
│  (Python 3.12)          │
│                         │
│  • Filter by class,     │
│    state, date range    │
│  • Pagination           │
│  • Aggregation stats    │
└─────────────────────────┘
        ▲
        │
┌─────────────────────────┐
│  API Gateway (REST)     │
│                         │
│  GET /recalls           │
│  GET /recalls/stats     │
│  GET /recalls/{id}      │
│                         │
│  CORS enabled           │
└─────────────────────────┘
        ▲
        │
┌─────────────────────────┐       ┌──────────────────────┐
│  CloudFront CDN         │◀──────│  S3 Bucket           │
│                         │       │  (React build files)  │
│  recallradar.your-      │       │                      │
│  domain.com             │       │  index.html          │
└─────────────────────────┘       │  static/js/          │
                                  │  static/css/         │
        Dashboard features:       └──────────────────────┘
        • Interactive US state map (color-coded by recall volume)
        • Live recall feed with severity badges
        • Stats panel (total active, by classification, top firms)
        • Filter by state, classification, date range
```

### Full Vision Architecture (Phase 1–7)

```
                          ┌─────────────────────────────┐
                          │    Data Sources              │
                          │                             │
                          │  openFDA (food/drug/device) │
                          │  CPSC (consumer products)   │
                          │  NHTSA (vehicles)           │
                          │  USDA FSIS (meat/poultry)   │
                          └──────────┬──────────────────┘
                                     │
                          EventBridge Scheduler
                                     │
                                     ▼
                          ┌─────────────────────────┐
                          │  Ingestion Lambdas      │
                          │  (one per data source)  │
                          └──────────┬──────────────┘
                                     │
                                     ▼
                          ┌─────────────────────────┐
                          │  Kinesis Data Stream     │  ◀── Phase 4
                          │  (unified recall events) │
                          └──────────┬──────────────┘
                                     │
                          ┌──────────┼──────────────┐
                          │          │              │
                          ▼          ▼              ▼
                    ┌──────────┐ ┌────────┐  ┌───────────┐
                    │ DynamoDB │ │Bedrock │  │Timestream │
                    │ (recalls)│ │(Claude)│  │(metrics)  │
                    └──────────┘ └────────┘  └───────────┘
                          │          │              │
                          │     AI enrichment:      │
                          │     • Risk scoring      │
                          │     • Plain-English     │
                          │       summaries         │
                          │     • Contamination     │
                          │       type tagging      │
                          │                         │
                          └──────────┬──────────────┘
                                     │
                          ┌─────────────────────────┐
                          │  API Gateway + Lambda   │
                          │  (REST + WebSocket)     │
                          └──────────┬──────────────┘
                                     │
                    ┌────────────────┬┴───────────────┐
                    │                │                │
              ┌──────────┐   ┌────────────┐   ┌────────────┐
              │ React    │   │ Cognito    │   │ SNS / SES  │
              │ Dashboard│   │ (user auth)│   │ (alerts)   │
              │ S3+CF    │   │ Phase 5    │   │ Phase 5    │
              └──────────┘   └────────────┘   └────────────┘
```

---

## 3. Data Sources (Verified Live)

### openFDA Food Enforcement API — Phase 1 primary source

| Detail | Value |
|---|---|
| **Endpoint** | `https://api.fda.gov/food/enforcement.json` |
| **Auth** | None required (40 req/min). Free API key available for 240 req/min. |
| **Records** | 28,876+ (as of June 2026) |
| **Coverage** | 2004–present |
| **Update frequency** | Weekly |
| **Last updated** | May 13, 2026 (confirmed live) |
| **Data format** | JSON |

**Key fields you'll use:**

```json
{
  "recall_number": "F-0276-2017",
  "classification": "Class II",
  "status": "Terminated",
  "report_date": "20161102",
  "recall_initiation_date": "20160808",
  "recalling_firm": "Pharmatech LLC",
  "product_description": "CytoDetox, Hydrolyzed Clinoptilolite...",
  "reason_for_recall": "Potential risk of product contamination with Burkholderia cepacia.",
  "distribution_pattern": "FL, MI, MS, and OH.",
  "city": "Davie",
  "state": "FL",
  "country": "United States",
  "voluntary_mandated": "Voluntary: Firm initiated",
  "product_quantity": "1,990 bottles",
  "code_info": "UPC No. 632687615989; Lot No. 30661601..."
}
```

**Important distinction:** The `state` field is where the recalling *firm* is located — NOT the affected states. The affected geography lives in `distribution_pattern` as free text. Parsing this is one of the key data manipulation challenges in Phase 1.

**Classification severity:**
- **Class I** — Dangerous or defective products that could cause serious health problems or death.
- **Class II** — Products that might cause a temporary health problem, or pose a slight threat of a serious nature.
- **Class III** — Products that are unlikely to cause any adverse health reaction, but violate FDA labeling or manufacturing laws.

### CPSC Recalls API — Phase 3 expansion

| Detail | Value |
|---|---|
| **Endpoint** | `https://www.saferproducts.gov/RestWebServices/Recall?format=json` |
| **Auth** | None required |
| **Records** | 9,000+ |
| **Coverage** | Consumer products (toys, electronics, furniture, etc.) |

### NHTSA Recalls API — Phase 3 expansion

| Detail | Value |
|---|---|
| **Endpoint** | `https://api.nhtsa.gov/recalls/recallsByVehicle` |
| **Auth** | None required |
| **Coverage** | Vehicle safety recalls |

### USDA FSIS — Phase 3 expansion

| Detail | Value |
|---|---|
| **Endpoint** | `https://www.fsis.usda.gov/recalls` (RSS/scrape) |
| **Coverage** | Meat, poultry, egg products |

---

## Phase 1A — DynamoDB Table Design

### Why this step first

You need to know what you're storing before you write the ingestion code. The table design drives everything downstream — the Lambda write pattern, the Query Lambda read pattern, and the dashboard's filtering capabilities.

### Table: `recallradar-recalls`

**Primary key design:**

| Attribute | Type | Role |
|---|---|---|
| `PK` | String | `recall_number` (e.g., `F-0276-2017`) — guaranteed unique per recall |
| `SK` | String | `source#report_date` (e.g., `FDA#20261102`) — enables querying by source and sorting by date |

**Attributes:**

| Attribute | Type | Description |
|---|---|---|
| `classification` | String | `Class I`, `Class II`, `Class III` |
| `status` | String | `Ongoing`, `Completed`, `Terminated` |
| `report_date` | String | `YYYYMMDD` format from openFDA |
| `recall_initiation_date` | String | When the recall was actually initiated |
| `recalling_firm` | String | Company name |
| `product_description` | String | What was recalled |
| `reason_for_recall` | String | Why — this is the narrative gold |
| `distribution_pattern` | String | Raw text from API (e.g., "FL, MI, MS, and OH.") |
| `affected_states` | List(String) | Parsed from `distribution_pattern` (your enrichment) |
| `is_nationwide` | Boolean | `true` if distribution_pattern contains "Nationwide" |
| `firm_city` | String | City of recalling firm |
| `firm_state` | String | State of recalling firm |
| `product_quantity` | String | How many units affected |
| `voluntary_mandated` | String | Who initiated the recall |
| `source` | String | `FDA`, `CPSC`, `NHTSA` — for multi-source expansion |
| `ingested_at` | String | ISO 8601 timestamp of when you ingested this record |

**Global Secondary Indexes (GSIs):**

| GSI Name | PK | SK | Use Case |
|---|---|---|---|
| `classification-date-index` | `classification` | `report_date` | "Show me all Class I recalls, most recent first" |
| `source-date-index` | `source` | `report_date` | "Show me all FDA recalls this month" (ready for multi-source) |
| `status-date-index` | `status` | `report_date` | "Show me all ongoing recalls" |

**Key design decision — why `recall_number` as PK:**

The openFDA API doesn't guarantee ordering on re-fetch, and the same recall can appear in multiple API calls. Using `recall_number` as PK gives you natural idempotency — `put_item` with the same recall_number simply overwrites, no deduplication logic needed. This is the same pattern you used with DynamoDB cooldown logic at DXC.

### Console steps

1. Go to **DynamoDB → Create table**
2. Table name: `recallradar-recalls`
3. Partition key: `PK` (String)
4. Sort key: `SK` (String)
5. Table settings: **Customize settings**
6. Capacity mode: **On-demand** (you don't know the write pattern yet, and it's free-tier eligible)
7. Create the table
8. Go to **Indexes tab → Create index** for each GSI above

### Move-on checklist

- [ ] Table created with PK/SK
- [ ] All three GSIs created and status ACTIVE
- [ ] You can see the table in the DynamoDB console with 0 items
- [ ] Screenshot captured: empty table with GSIs visible

---

## Phase 1B — Ingestion Lambda

### What this Lambda does

1. Calls the openFDA food enforcement API
2. Fetches the most recent recalls (last 90 days, paginated)
3. Parses the `distribution_pattern` field into a clean list of affected states
4. Writes each recall to DynamoDB (idempotent — safe to run repeatedly)
5. Returns a count of records ingested

### IAM Role: `recallradar-ingestion-role`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBWrite",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:BatchWriteItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/recallradar-recalls"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:ACCOUNT_ID:*"
    }
  ]
}
```

### Starter code: `lambda/ingestion/handler.py`

```python
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
from botocore.exceptions import ClientError

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
        # Match isolated 2-letter caps that are real state codes
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

            # Parse distribution pattern
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
```

### Console steps

1. Go to **Lambda → Create function**
2. Function name: `recallradar-ingestion`
3. Runtime: **Python 3.12**
4. Architecture: **arm64** (cost-efficient)
5. Execution role: Create new role `recallradar-ingestion-role` with the policy above
6. Create function
7. Paste the code above into the inline editor
8. **Configuration → General configuration → Edit:**
   - Memory: **256 MB**
   - Timeout: **2 minutes** (openFDA pagination can be slow)
9. **Configuration → Environment variables:**
   - `TABLE_NAME` = `recallradar-recalls`
   - `LOOKBACK_DAYS` = `90`
10. **Test** with empty event `{}` — verify records appear in DynamoDB

### Move-on checklist

- [ ] Lambda created with Python 3.12 / arm64
- [ ] IAM role has DynamoDB write + CloudWatch logs permissions only
- [ ] Test invocation succeeds — check CloudWatch logs for record count
- [ ] DynamoDB table shows items with `PK`, `SK`, `affected_states` populated
- [ ] Run it twice — item count should NOT double (idempotent writes confirmed)
- [ ] Screenshot: DynamoDB table with populated items
- [ ] Screenshot: CloudWatch log showing "Ingestion complete — N records written"

---

## Phase 1C — State Parsing & Geocoding

### What this step adds

The state parsing logic is already embedded in the Ingestion Lambda above (the `parse_distribution_pattern` function). This phase is about **verifying it works** and adding a **static geocoding layer** for the dashboard map.

### State coordinate reference

The dashboard needs lat/lng centroids for each state to place pins on the map. This is static data — store it as a constant in your frontend code or as a separate DynamoDB reference table.

```python
# Use this in the Query Lambda or ship it to the React frontend as a static import
STATE_COORDINATES = {
    "AL": {"lat": 32.806671, "lng": -86.791130, "name": "Alabama"},
    "AK": {"lat": 61.370716, "lng": -152.404419, "name": "Alaska"},
    "AZ": {"lat": 33.729759, "lng": -111.431221, "name": "Arizona"},
    "AR": {"lat": 34.969704, "lng": -92.373123, "name": "Arkansas"},
    "CA": {"lat": 36.116203, "lng": -119.681564, "name": "California"},
    "CO": {"lat": 39.059811, "lng": -105.311104, "name": "Colorado"},
    "CT": {"lat": 41.597782, "lng": -72.755371, "name": "Connecticut"},
    "DE": {"lat": 39.318523, "lng": -75.507141, "name": "Delaware"},
    "FL": {"lat": 27.766279, "lng": -81.686783, "name": "Florida"},
    "GA": {"lat": 33.040619, "lng": -83.643074, "name": "Georgia"},
    "HI": {"lat": 21.094318, "lng": -157.498337, "name": "Hawaii"},
    "ID": {"lat": 44.240459, "lng": -114.478828, "name": "Idaho"},
    "IL": {"lat": 40.349457, "lng": -88.986137, "name": "Illinois"},
    "IN": {"lat": 39.849426, "lng": -86.258278, "name": "Indiana"},
    "IA": {"lat": 42.011539, "lng": -93.210526, "name": "Iowa"},
    "KS": {"lat": 38.526600, "lng": -96.726486, "name": "Kansas"},
    "KY": {"lat": 37.668140, "lng": -84.670067, "name": "Kentucky"},
    "LA": {"lat": 31.169546, "lng": -91.867805, "name": "Louisiana"},
    "ME": {"lat": 44.693947, "lng": -69.381927, "name": "Maine"},
    "MD": {"lat": 39.063946, "lng": -76.802101, "name": "Maryland"},
    "MA": {"lat": 42.230171, "lng": -71.530106, "name": "Massachusetts"},
    "MI": {"lat": 43.326618, "lng": -84.536095, "name": "Michigan"},
    "MN": {"lat": 45.694454, "lng": -93.900192, "name": "Minnesota"},
    "MS": {"lat": 32.741646, "lng": -89.678696, "name": "Mississippi"},
    "MO": {"lat": 38.456085, "lng": -92.288368, "name": "Missouri"},
    "MT": {"lat": 46.921925, "lng": -110.454353, "name": "Montana"},
    "NE": {"lat": 41.125370, "lng": -98.268082, "name": "Nebraska"},
    "NV": {"lat": 38.313515, "lng": -117.055374, "name": "Nevada"},
    "NH": {"lat": 43.452492, "lng": -71.563896, "name": "New Hampshire"},
    "NJ": {"lat": 40.298904, "lng": -74.521011, "name": "New Jersey"},
    "NM": {"lat": 34.840515, "lng": -106.248482, "name": "New Mexico"},
    "NY": {"lat": 42.165726, "lng": -74.948051, "name": "New York"},
    "NC": {"lat": 35.630066, "lng": -79.806419, "name": "North Carolina"},
    "ND": {"lat": 47.528912, "lng": -99.784012, "name": "North Dakota"},
    "OH": {"lat": 40.388783, "lng": -82.764915, "name": "Ohio"},
    "OK": {"lat": 35.565342, "lng": -96.928917, "name": "Oklahoma"},
    "OR": {"lat": 44.572021, "lng": -122.070938, "name": "Oregon"},
    "PA": {"lat": 40.590752, "lng": -77.209755, "name": "Pennsylvania"},
    "RI": {"lat": 41.680893, "lng": -71.511780, "name": "Rhode Island"},
    "SC": {"lat": 33.856892, "lng": -80.945007, "name": "South Carolina"},
    "SD": {"lat": 44.299782, "lng": -99.438828, "name": "South Dakota"},
    "TN": {"lat": 35.747845, "lng": -86.692345, "name": "Tennessee"},
    "TX": {"lat": 31.054487, "lng": -97.563461, "name": "Texas"},
    "UT": {"lat": 40.150032, "lng": -111.862434, "name": "Utah"},
    "VT": {"lat": 44.045876, "lng": -72.710686, "name": "Vermont"},
    "VA": {"lat": 37.769337, "lng": -78.169968, "name": "Virginia"},
    "WA": {"lat": 47.400902, "lng": -121.490494, "name": "Washington"},
    "WV": {"lat": 38.491226, "lng": -80.954453, "name": "West Virginia"},
    "WI": {"lat": 44.268543, "lng": -89.616508, "name": "Wisconsin"},
    "WY": {"lat": 42.755966, "lng": -107.302490, "name": "Wyoming"},
    "DC": {"lat": 38.897438, "lng": -77.026817, "name": "District of Columbia"}
}
```

### Verification

After running the Ingestion Lambda, spot-check 5–10 DynamoDB items:

1. Find a recall with `distribution_pattern` = `"FL, MI, MS, and OH."` → `affected_states` should be `["FL", "MI", "MS", "OH"]`
2. Find a recall with `distribution_pattern` containing `"Nationwide"` → `is_nationwide` should be `true`, `affected_states` should have 50 entries
3. Find a recall with `distribution_pattern` = `"State of California"` → `affected_states` should be `["CA"]`

If edge cases fail, refine the `parse_distribution_pattern` function. The distribution_pattern field is notoriously inconsistent — treating this as an evolving parser is realistic and defensible in an interview.

### Move-on checklist

- [ ] Spot-checked 5+ items — `affected_states` correctly parsed
- [ ] Nationwide recalls have `is_nationwide: true`
- [ ] State-specific recalls have correct abbreviation lists
- [ ] Edge cases documented (any patterns that didn't parse? Note them for Phase 2 AI enrichment)

---

## Phase 1D — EventBridge Scheduler

### What this configures

A scheduled trigger that invokes the Ingestion Lambda every 6 hours. openFDA updates weekly, so 6 hours gives you near-real-time coverage without wasting invocations.

### Console steps

1. Go to **Amazon EventBridge → Schedules → Create schedule**
2. Schedule name: `recallradar-ingestion-schedule`
3. Schedule type: **Recurring schedule**
4. Schedule expression: `rate(6 hours)`
5. Flexible time window: **15 minutes** (avoids thundering herd if you add more schedules later)
6. Target: **AWS Lambda → `recallradar-ingestion`**
7. Payload: `{}` (empty JSON)
8. Retry policy: **Max retries: 2**, **Max event age: 1 hour**
9. Dead-letter queue: Create an SQS queue `recallradar-dlq` and attach it (captures failed invocations)
10. Create schedule

### Key design decision — why 6 hours, not 15 minutes

openFDA updates weekly. Polling every 15 minutes means 672 invocations/week to catch 1 update. Every 6 hours means 28 invocations/week — still catches the weekly update within hours, but costs ~24x fewer Lambda invocations. For a portfolio project, this matters for cost. For the interview conversation, it shows you think about operational efficiency, not just "make it work."

When you add CPSC and NHTSA (which update more frequently), you can create separate schedules with different intervals per source.

### Move-on checklist

- [ ] Schedule created and enabled
- [ ] DLQ created and attached
- [ ] Wait 6+ hours and verify a second invocation ran (check CloudWatch logs)
- [ ] DynamoDB item count is stable (idempotent — shouldn't spike)
- [ ] Screenshot: EventBridge schedule configuration

---

## Phase 1E — Query Lambda + API Gateway

### What this builds

A REST API that the React dashboard will call to fetch recall data. Three endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /recalls` | Paginated list with filters (classification, state, date range, status) |
| `GET /recalls/stats` | Aggregated statistics (counts by classification, top firms, top states) |
| `GET /recalls/{recall_number}` | Single recall detail |

### IAM Role: `recallradar-query-role`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBRead",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/recallradar-recalls",
        "arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/recallradar-recalls/index/*"
      ]
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:ACCOUNT_ID:*"
    }
  ]
}
```

### Starter code: `lambda/query/handler.py`

```python
"""
RecallRadar — Query Lambda
Serves recall data to the React dashboard via API Gateway.
"""

import json
import os
import logging
from decimal import Decimal
from collections import Counter

import boto3
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("TABLE_NAME", "recallradar-recalls")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

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
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": json.dumps(body, cls=DecimalEncoder)
    }


# ──────────────────────────────────────────────
# Route: GET /recalls
# ──────────────────────────────────────────────

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

    # Use GSI if filtering by classification (most common dashboard filter)
    if classification and not state:
        query_kwargs = {
            "IndexName": "classification-date-index",
            "KeyConditionExpression": Key("classification").eq(classification),
            "ScanIndexForward": False,  # newest first
            "Limit": limit
        }

        # Add date range if provided
        if from_date and to_date:
            query_kwargs["KeyConditionExpression"] &= Key("report_date").between(from_date, to_date)
        elif from_date:
            query_kwargs["KeyConditionExpression"] &= Key("report_date").gte(from_date)

        if next_token:
            query_kwargs["ExclusiveStartKey"] = json.loads(next_token)

        response = table.query(**query_kwargs)

    else:
        # Fall back to scan with filters
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
        "count": len(items)
    }

    if "LastEvaluatedKey" in response:
        result["next_token"] = json.dumps(response["LastEvaluatedKey"], cls=DecimalEncoder)

    return result


# ──────────────────────────────────────────────
# Route: GET /recalls/stats
# ──────────────────────────────────────────────

def get_recall_stats() -> dict:
    """
    Aggregated statistics across all recalls.
    Note: Scans entire table — in Phase 4, precompute these with Timestream.
    """
    items = []
    scan_kwargs = {
        "ProjectionExpression": "classification, #s, recalling_firm, affected_states, is_nationwide, report_date",
        "ExpressionAttributeNames": {"#s": "status"}
    }

    # Paginate full scan
    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    # Compute aggregations
    classification_counts = Counter(item.get("classification", "Unknown") for item in items)
    status_counts = Counter(item.get("status", "Unknown") for item in items)
    firm_counts = Counter(item.get("recalling_firm", "Unknown") for item in items)

    # State frequency — how many recalls affect each state
    state_counts = Counter()
    for item in items:
        for state in item.get("affected_states", []):
            state_counts[state] += 1

    # Nationwide percentage
    nationwide_count = sum(1 for item in items if item.get("is_nationwide"))

    return {
        "total_recalls": len(items),
        "by_classification": dict(classification_counts),
        "by_status": dict(status_counts),
        "top_firms": dict(firm_counts.most_common(10)),
        "top_states": dict(state_counts.most_common(10)),
        "nationwide_count": nationwide_count,
        "nationwide_percentage": round(
            (nationwide_count / len(items) * 100) if items else 0, 1
        )
    }


# ──────────────────────────────────────────────
# Route: GET /recalls/{recall_number}
# ──────────────────────────────────────────────

def get_recall_detail(recall_number: str) -> dict:
    """Fetch a single recall by recall_number (PK)."""
    response = table.query(
        KeyConditionExpression=Key("PK").eq(recall_number),
        Limit=1
    )
    items = response.get("Items", [])
    if not items:
        return None
    return items[0]


# ──────────────────────────────────────────────
# Lambda Handler (API Gateway router)
# ──────────────────────────────────────────────

def lambda_handler(event, context):
    """Routes API Gateway requests to the appropriate handler."""
    logger.info(f"Received event: {json.dumps(event)}")

    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/")
    params = event.get("queryStringParameters") or {}
    path_params = event.get("pathParameters") or {}

    # Handle CORS preflight
    if http_method == "OPTIONS":
        return cors_response(200, {"message": "OK"})

    try:
        if path == "/recalls/stats":
            result = get_recall_stats()
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
```

### API Gateway console steps

1. Go to **API Gateway → Create API → REST API** (not HTTP API — REST gives you more control for portfolio demo)
2. API name: `recallradar-api`
3. Create resources and methods:

```
/recalls
    GET  → recallradar-query Lambda (proxy integration)
    OPTIONS → Mock integration (CORS)

/recalls/stats
    GET  → recallradar-query Lambda (proxy integration)
    OPTIONS → Mock integration (CORS)

/recalls/{recall_number}
    GET  → recallradar-query Lambda (proxy integration)
    OPTIONS → Mock integration (CORS)
```

4. Enable **Lambda proxy integration** on each GET method
5. Deploy API to a stage called `v1`
6. Note the invoke URL: `https://XXXXXXXX.execute-api.us-east-1.amazonaws.com/v1`

### Testing

```bash
# Fetch recalls
curl "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/v1/recalls?limit=5"

# Filter by Class I
curl "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/v1/recalls?classification=Class%20I&limit=5"

# Filter by state
curl "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/v1/recalls?state=LA&limit=10"

# Get stats
curl "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/v1/recalls/stats"
```

### Move-on checklist

- [ ] Query Lambda created with DynamoDB read-only permissions
- [ ] API Gateway deployed with `/recalls`, `/recalls/stats`, `/recalls/{recall_number}`
- [ ] CORS headers returned on all responses
- [ ] All three endpoints return valid JSON from curl
- [ ] Filtering by classification works
- [ ] Filtering by state works
- [ ] Stats endpoint returns aggregated counts
- [ ] Screenshot: API Gateway resource tree
- [ ] Screenshot: curl output from `/recalls/stats`

---

## Phase 1F — React Dashboard

### What you're building

A single-page React app with three panels:

1. **US Map** — States color-coded by recall volume (heat map). Click a state to filter.
2. **Live Feed** — Scrollable list of recent recalls with severity badges (red/orange/yellow for Class I/II/III).
3. **Stats Panel** — Total recalls, breakdown by classification, top firms, top states.

### Key library choices

| Library | Purpose | Why this one |
|---|---|---|
| `react-simple-maps` | US state map SVG | Free, no API key, lightweight, state-level granularity |
| `recharts` | Bar/pie charts for stats | Already in your project toolbox, clean defaults |
| `d3-scale` | Color scale for heat map | Pairs with react-simple-maps, industry standard |

### Project setup

```bash
npx create-react-app recallradar-dashboard
cd recallradar-dashboard
npm install react-simple-maps recharts d3-scale
```

### Core component: `src/App.js`

```jsx
import React, { useState, useEffect, useCallback } from "react";
import { RecallMap } from "./components/RecallMap";
import { RecallFeed } from "./components/RecallFeed";
import { StatsPanel } from "./components/StatsPanel";
import { FilterBar } from "./components/FilterBar";
import "./App.css";

const API_BASE = process.env.REACT_APP_API_URL || "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/v1";

function App() {
  const [recalls, setRecalls] = useState([]);
  const [stats, setStats] = useState(null);
  const [filters, setFilters] = useState({
    classification: null,
    state: null,
    status: "Ongoing",
  });
  const [loading, setLoading] = useState(true);

  const fetchRecalls = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    params.set("limit", "50");
    if (filters.classification) params.set("classification", filters.classification);
    if (filters.state) params.set("state", filters.state);
    if (filters.status) params.set("status", filters.status);

    try {
      const res = await fetch(`${API_BASE}/recalls?${params}`);
      const data = await res.json();
      setRecalls(data.recalls || []);
    } catch (err) {
      console.error("Failed to fetch recalls:", err);
    }
    setLoading(false);
  }, [filters]);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/recalls/stats`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    }
  }, []);

  useEffect(() => { fetchRecalls(); }, [fetchRecalls]);
  useEffect(() => { fetchStats(); }, [fetchStats]);

  const handleStateClick = (stateCode) => {
    setFilters((prev) => ({
      ...prev,
      state: prev.state === stateCode ? null : stateCode,
    }));
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>RecallRadar</h1>
        <p className="subtitle">
          Real-time FDA food recall intelligence across the United States
        </p>
      </header>

      <FilterBar filters={filters} onChange={setFilters} />

      <main className="dashboard">
        <section className="map-section">
          <RecallMap
            stats={stats}
            selectedState={filters.state}
            onStateClick={handleStateClick}
          />
        </section>

        <aside className="sidebar">
          <StatsPanel stats={stats} loading={!stats} />
          <RecallFeed recalls={recalls} loading={loading} />
        </aside>
      </main>
    </div>
  );
}

export default App;
```

### Core component: `src/components/RecallMap.js`

```jsx
import React, { useMemo } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
} from "react-simple-maps";
import { scaleQuantize } from "d3-scale";

const GEO_URL = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

// FIPS → state abbreviation for matching with your data
const FIPS_TO_STATE = {
  "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
  "08": "CO", "09": "CT", "10": "DE", "12": "FL", "13": "GA",
  "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA",
  "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
  "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO",
  "30": "MT", "31": "NE", "32": "NV", "33": "NH", "34": "NJ",
  "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
  "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC",
  "46": "SD", "47": "TN", "48": "TX", "49": "UT", "50": "VT",
  "51": "VA", "53": "WA", "54": "WV", "55": "WI", "56": "WY",
  "11": "DC"
};

export function RecallMap({ stats, selectedState, onStateClick }) {
  const colorScale = useMemo(() => {
    if (!stats?.top_states) return () => "#EEE";
    const values = Object.values(stats.top_states);
    const max = Math.max(...values, 1);
    return scaleQuantize()
      .domain([0, max])
      .range([
        "#fee5d9", "#fcbba1", "#fc9272",
        "#fb6a4a", "#ef3b2c", "#cb181d", "#99000d"
      ]);
  }, [stats]);

  return (
    <ComposableMap projection="geoAlbersUsa">
      <Geographies geography={GEO_URL}>
        {({ geographies }) =>
          geographies.map((geo) => {
            const stateCode = FIPS_TO_STATE[geo.id];
            const count = stats?.top_states?.[stateCode] || 0;
            const isSelected = selectedState === stateCode;

            return (
              <Geography
                key={geo.rsmKey}
                geography={geo}
                onClick={() => onStateClick(stateCode)}
                style={{
                  default: {
                    fill: isSelected ? "#2563eb" : colorScale(count),
                    stroke: "#fff",
                    strokeWidth: 0.5,
                    outline: "none",
                  },
                  hover: {
                    fill: "#3b82f6",
                    stroke: "#fff",
                    strokeWidth: 1,
                    outline: "none",
                    cursor: "pointer",
                  },
                  pressed: { outline: "none" },
                }}
              />
            );
          })
        }
      </Geographies>
    </ComposableMap>
  );
}
```

### Core component: `src/components/RecallFeed.js`

```jsx
import React from "react";

const SEVERITY_COLORS = {
  "Class I": { bg: "#fef2f2", border: "#dc2626", text: "#991b1b", label: "CRITICAL" },
  "Class II": { bg: "#fff7ed", border: "#ea580c", text: "#9a3412", label: "MODERATE" },
  "Class III": { bg: "#fefce8", border: "#ca8a04", text: "#854d0e", label: "LOW" },
};

export function RecallFeed({ recalls, loading }) {
  if (loading) return <div className="feed-loading">Loading recalls...</div>;

  return (
    <div className="recall-feed">
      <h2>Recent Recalls</h2>
      {recalls.length === 0 && <p className="no-results">No recalls match your filters.</p>}
      {recalls.map((recall) => {
        const severity = SEVERITY_COLORS[recall.classification] || SEVERITY_COLORS["Class III"];
        return (
          <article
            key={recall.PK}
            className="recall-card"
            style={{ borderLeft: `4px solid ${severity.border}` }}
          >
            <div className="recall-header">
              <span
                className="severity-badge"
                style={{ background: severity.bg, color: severity.text }}
              >
                {severity.label}
              </span>
              <span className="recall-date">
                {formatDate(recall.report_date)}
              </span>
            </div>
            <h3 className="recall-firm">{recall.recalling_firm}</h3>
            <p className="recall-product">
              {truncate(recall.product_description, 120)}
            </p>
            <p className="recall-reason">
              {truncate(recall.reason_for_recall, 150)}
            </p>
            {recall.is_nationwide ? (
              <span className="distribution-tag nationwide">Nationwide</span>
            ) : (
              <span className="distribution-tag">
                {(recall.affected_states || []).join(", ")}
              </span>
            )}
          </article>
        );
      })}
    </div>
  );
}

function formatDate(dateStr) {
  if (!dateStr || dateStr.length !== 8) return dateStr;
  return `${dateStr.slice(4, 6)}/${dateStr.slice(6, 8)}/${dateStr.slice(0, 4)}`;
}

function truncate(str, max) {
  if (!str) return "";
  return str.length > max ? str.slice(0, max) + "..." : str;
}
```

### Core component: `src/components/StatsPanel.js`

```jsx
import React from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const CLASS_COLORS = {
  "Class I": "#dc2626",
  "Class II": "#ea580c",
  "Class III": "#ca8a04",
};

export function StatsPanel({ stats, loading }) {
  if (loading || !stats) return <div className="stats-loading">Loading stats...</div>;

  const classData = Object.entries(stats.by_classification || {}).map(
    ([name, value]) => ({ name, value })
  );

  const firmData = Object.entries(stats.top_firms || {})
    .slice(0, 5)
    .map(([name, value]) => ({
      name: name.length > 20 ? name.slice(0, 18) + "..." : name,
      value,
    }));

  return (
    <div className="stats-panel">
      <h2>Overview</h2>

      <div className="stat-cards">
        <div className="stat-card">
          <span className="stat-number">{stats.total_recalls?.toLocaleString()}</span>
          <span className="stat-label">Total Recalls</span>
        </div>
        <div className="stat-card">
          <span className="stat-number">{stats.by_classification?.["Class I"] || 0}</span>
          <span className="stat-label critical">Class I (Critical)</span>
        </div>
        <div className="stat-card">
          <span className="stat-number">{stats.nationwide_percentage}%</span>
          <span className="stat-label">Nationwide</span>
        </div>
      </div>

      <h3>By Classification</h3>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={classData} layout="vertical">
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" width={60} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {classData.map((entry) => (
              <Cell key={entry.name} fill={CLASS_COLORS[entry.name] || "#888"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <h3>Top Firms</h3>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={firmData} layout="vertical">
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### Core component: `src/components/FilterBar.js`

```jsx
import React from "react";

export function FilterBar({ filters, onChange }) {
  const update = (key, value) => {
    onChange((prev) => ({
      ...prev,
      [key]: prev[key] === value ? null : value,
    }));
  };

  return (
    <div className="filter-bar">
      <div className="filter-group">
        <label>Severity</label>
        <div className="filter-buttons">
          {["Class I", "Class II", "Class III"].map((cls) => (
            <button
              key={cls}
              className={`filter-btn ${filters.classification === cls ? "active" : ""}`}
              onClick={() => update("classification", cls)}
            >
              {cls}
            </button>
          ))}
        </div>
      </div>

      <div className="filter-group">
        <label>Status</label>
        <div className="filter-buttons">
          {["Ongoing", "Completed", "Terminated"].map((status) => (
            <button
              key={status}
              className={`filter-btn ${filters.status === status ? "active" : ""}`}
              onClick={() => update("status", status)}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {filters.state && (
        <div className="active-filter">
          Showing: {filters.state}
          <button onClick={() => update("state", null)} className="clear-btn">
            ×
          </button>
        </div>
      )}
    </div>
  );
}
```

### Move-on checklist

- [ ] React app scaffolded with `create-react-app`
- [ ] All four components created (`RecallMap`, `RecallFeed`, `StatsPanel`, `FilterBar`)
- [ ] Dashboard loads and displays real data from your API
- [ ] Map renders all 50 states with heat-map coloring
- [ ] Clicking a state filters the recall feed
- [ ] Classification filter buttons work
- [ ] Stats panel shows aggregated counts and charts
- [ ] GIF/screen recording captured of dashboard in action (this is your README hero asset)

---

## Phase 1G — S3 + CloudFront Hosting

### What this deploys

Your built React app, served globally via CloudFront CDN with HTTPS.

### Steps

1. **Build the React app:**
   ```bash
   cd recallradar-dashboard
   npm run build
   ```

2. **Create S3 bucket:**
   - Bucket name: `recallradar-dashboard-ACCOUNT_ID` (must be globally unique)
   - Region: `us-east-1`
   - Block all public access: **ON** (CloudFront will access it via OAC)
   - Upload the contents of `build/` to the bucket

3. **Create CloudFront distribution:**
   - Origin: Your S3 bucket
   - Origin access: **Origin access control (OAC)** — create a new OAC
   - Default root object: `index.html`
   - Custom error responses: Add 403 and 404 → redirect to `/index.html` with 200 (SPA routing)
   - Copy the S3 bucket policy CloudFront generates and apply it to your bucket

4. **Update React app:**
   - Set `REACT_APP_API_URL` to your API Gateway URL in `.env.production`
   - Rebuild and re-upload

### Key design decision — why OAC over public bucket

A public S3 bucket is the fast path. But OAC (Origin Access Control) is the production-correct pattern: the bucket stays private, only CloudFront can read it, and you can add WAF later. For a security-focused portfolio, deploying with a public bucket would be a visible inconsistency. This decision goes in your Key Design Decisions section.

### Move-on checklist

- [ ] S3 bucket created with public access blocked
- [ ] CloudFront distribution deployed with OAC
- [ ] Dashboard loads via CloudFront URL (HTTPS)
- [ ] SPA routing works (direct URL access to `/recalls` doesn't 404)
- [ ] Screenshot: CloudFront distribution settings
- [ ] Note the CloudFront URL — this goes in your README

---

## Phase 1H — Monitoring & Hardening

### What this adds

Production-grade observability for a system that runs continuously. This is what separates "I deployed it once" from "this thing actually runs."

### CloudWatch Dashboard

Create a dashboard named `RecallRadar-Operations` with these widgets:

1. **Ingestion Lambda invocations** (count, 6h period) — should show regular heartbeat
2. **Ingestion Lambda errors** (count) — should be 0
3. **Ingestion Lambda duration** (avg, max) — track if API is slowing down
4. **DynamoDB read/write capacity consumed** — verify you're in free tier
5. **API Gateway 4xx/5xx rates** — catch frontend bugs or abuse
6. **DLQ message count** — should be 0

### CloudWatch Alarms

| Alarm | Metric | Threshold | Action |
|---|---|---|---|
| `recallradar-ingestion-errors` | Lambda errors | > 0 for 1 period | SNS email notification |
| `recallradar-dlq-messages` | SQS ApproximateNumberOfMessagesVisible | > 0 | SNS email notification |
| `recallradar-api-5xx` | API Gateway 5XXError | > 5 in 5 min | SNS email notification |

### Error handling hardening

Add to Ingestion Lambda:
- Catch individual record failures without aborting the batch
- Log failed recall_numbers for manual investigation
- Set CloudWatch metric for parse failures (tracks distribution_pattern edge cases)

### Move-on checklist

- [ ] CloudWatch dashboard created with all 6 widgets
- [ ] At least 2 alarms configured (ingestion errors + DLQ)
- [ ] Verified alarms trigger correctly (test by temporarily breaking the Lambda)
- [ ] Screenshot: CloudWatch dashboard showing healthy system
- [ ] Screenshot: Alarm configuration

---

## Phase 1I — Documentation & Portfolio

### README wireframe (aligned to your template)

Use the README Structure Template. Here's how each section maps:

**1. Title + One-Line Description:**
> RecallRadar — A real-time recall intelligence platform that ingests FDA food recall data, maps geographic impact across the United States, and surfaces insights about recall severity, frequency, and trends that nobody else aggregates.

**2. Tech Stack Badges:**
```
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)
![AWS Lambda](https://img.shields.io/badge/AWS_Lambda-FF9900?style=flat&logo=amazon-aws&logoColor=white)
![DynamoDB](https://img.shields.io/badge/DynamoDB-4053D6?style=flat&logo=amazon-dynamodb&logoColor=white)
![API Gateway](https://img.shields.io/badge/API_Gateway-FF4F8B?style=flat&logo=amazon-api-gateway&logoColor=white)
![CloudFront](https://img.shields.io/badge/CloudFront-8C4FFF?style=flat&logo=amazon-aws&logoColor=white)
![EventBridge](https://img.shields.io/badge/EventBridge-FF4F8B?style=flat&logo=amazon-aws&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=flat&logo=terraform&logoColor=white)
```

**3. Architecture Diagram:**
Use the ASCII diagram from Section 2 of this guide, or generate a visual with Kiro.

**4. How It Works:**
Walk through the full data flow: EventBridge → Lambda → openFDA → parse → DynamoDB → API Gateway → React dashboard.

**5. Key Design Decisions (minimum 5):**

| Decision | Why |
|---|---|
| `recall_number` as DynamoDB PK | Natural idempotency — re-running ingestion never creates duplicates. Same pattern as stateful deduplication in production alert systems. |
| On-demand DynamoDB capacity | Write pattern is bursty (batch after each API poll) with long idle periods between. Provisioned capacity would waste money on a system that writes once every 6 hours. |
| 6-hour polling instead of continuous | openFDA updates weekly. Polling every 15 min = 672 invocations to catch 1 update. 6 hours = 28 invocations. Operational efficiency over aggressive freshness. |
| OAC over public S3 bucket | CloudFront Origin Access Control keeps the S3 bucket private. A public bucket on a security engineer's portfolio would be a visible inconsistency. |
| State parsing as a Python function, not Bedrock | `distribution_pattern` has limited patterns — regex handles 95% of cases. Calling Bedrock for string parsing at ingestion time adds cost and latency that isn't justified. AI enrichment (Phase 2) targets higher-value analysis like risk scoring. |
| Scan for stats endpoint (Phase 1) | Full table scan is acceptable when the table has < 30K items and the stats endpoint is called infrequently. DynamoDB Streams + precomputed aggregations (Phase 4) replace this before scale matters. |

**Screenshots to capture (priority order):**
1. GIF/recording of the live dashboard (map + feed + filters in action)
2. CloudWatch dashboard showing healthy 24h+ operation
3. DynamoDB table view with populated items
4. EventBridge schedule configuration
5. API Gateway resource tree

### Repo structure

```
RecallRadar/
├── lambda/
│   ├── ingestion/
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── query/
│       ├── handler.py
│       └── requirements.txt
├── dashboard/
│   ├── src/
│   │   ├── components/
│   │   │   ├── RecallMap.js
│   │   │   ├── RecallFeed.js
│   │   │   ├── StatsPanel.js
│   │   │   └── FilterBar.js
│   │   ├── App.js
│   │   └── App.css
│   ├── public/
│   └── package.json
├── terraform/                  # Phase 2+
│   ├── main.tf
│   ├── variables.tf
│   └── modules/
├── images/
│   ├── architecture.png
│   ├── dashboard-demo.gif
│   └── cloudwatch-dashboard.png
├── docs/
│   └── API.md                  # API reference
└── README.md
```

### Move-on checklist

- [ ] README completed with all MUST sections from template
- [ ] Key Design Decisions section has 5+ entries with tradeoff reasoning
- [ ] Architecture diagram in README (ASCII or image)
- [ ] Dashboard GIF captured and embedded in README
- [ ] Repo pushed to GitHub as `RecallRadar`
- [ ] README has no "in progress" language — describe what exists, not what's planned (use "Future Improvements" section for that)

---

## Extension Roadmap (Phases 2–7)

Each phase below is a standalone enhancement you can add whenever you want. The project is designed so none of these require refactoring Phase 1 — they layer on top.

### Phase 2 — AI Enrichment (Bedrock)

**What it adds:** Bedrock (Claude Haiku) analyzes each recall's `reason_for_recall` and generates:
- Plain-English risk summary (no jargon)
- Contamination type tag (biological, chemical, physical, allergen, labeling)
- AI severity score (1–10) independent of FDA classification
- Consumer action recommendation

**New services:** Amazon Bedrock (Claude 3 Haiku)

**Architecture change:** Add a second Lambda in the ingestion pipeline that runs after the DynamoDB write — reads new items via DynamoDB Streams, calls Bedrock, writes the enrichment back to the same item.

**Portfolio impact:** Brings your two-model Bedrock strategy into this project. The contrast between "FDA says Class II" and "AI scores this 8/10 because Listeria in ready-to-eat food affects immunocompromised populations" is a powerful demo.

### Phase 3 — Multi-Source Expansion (CPSC, NHTSA, USDA)

**What it adds:** Three new Ingestion Lambdas, one per source. Same pattern, different API adapters. Dashboard gets source tabs and cross-source analytics.

**New services:** None — reuses the same architecture.

**Portfolio impact:** Shows you can design a pluggable system. Each data source is a new Lambda with the same interface contract → same DynamoDB table → same query API. This is the adapter pattern, and naming it in an interview earns points.

### Phase 4 — Trend Intelligence (Timestream)

**What it adds:** Time-series analytics: recall volume over time, seasonal contamination patterns, company recall history, average time between recall initiation and report date.

**New services:** Amazon Timestream

**Architecture change:** Ingestion Lambda writes a time-series record to Timestream alongside DynamoDB. New API endpoints serve time-series queries. Dashboard gets trend charts (line graphs, sparklines).

**Portfolio impact:** Timestream is a differentiator service — most portfolios don't include it. Time-series analysis is where the "interesting insights" vision really pays off.

### Phase 5 — User Subscriptions & Alerts (Cognito + SNS)

**What it adds:** User sign-up, location preferences, dietary restrictions. When a recall matches your profile (your state + your allergens), you get an SNS/SES alert.

**New services:** Amazon Cognito, SNS topic subscriptions, SES templated emails

**Portfolio impact:** Turns RecallRadar from a dashboard into a product. Cognito auth is expected at the senior level and absent from your current portfolio.

### Phase 6 — Predictive & Correlation Analytics

**What it adds:** Correlate recall patterns with FDA inspection data (also available via openFDA). Can you predict which companies are likely to have a recall based on inspection history? ML pipeline territory.

**New services:** SageMaker or Bedrock for correlation analysis

**Portfolio impact:** This is the "senior architect" extension — designing a predictive system, not just a reactive one.

### Phase 7+ — The Keep Going List

- NLP analysis of recall reason narratives (topic modeling, clustering)
- Grocery chain distribution mapping (which stores are affected?)
- Public REST API for third-party consumption (you become the data provider)
- Mobile PWA with push notifications
- Embeddable widget for local news sites
- Historical comparison dashboards (is food safety getting better or worse?)
- WebSocket API for real-time feed updates
- Integration with state health department data
- Recipe/meal planning integration ("flag if any ingredients in this recipe have active recalls")
- Chrome extension that checks recall status while grocery shopping online

---

## Cost Estimate (Phase 1 MVP)

| Service | Usage | Monthly Cost |
|---|---|---|
| Lambda (ingestion) | ~120 invocations/month, 256MB, ~30s avg | Free tier |
| Lambda (query) | ~1000 invocations/month, 128MB, ~1s avg | Free tier |
| DynamoDB (on-demand) | ~30K items, ~5K reads/month | Free tier |
| API Gateway | ~1000 requests/month | Free tier |
| EventBridge Scheduler | 4 invocations/day | Free tier |
| S3 | ~50MB static files | $0.01 |
| CloudFront | ~1GB transfer/month | Free tier (1TB/month) |
| CloudWatch | Dashboard + 2 alarms | ~$3.00 |
| SQS (DLQ) | Near-zero messages | Free tier |
| **Total** | | **~$3/month** |

This is a project that can run indefinitely for essentially nothing. That's part of the story — designing cost-efficient architectures is a skill that matters at Booz Allen's scale.
