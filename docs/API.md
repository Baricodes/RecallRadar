# RecallRadar API Reference

Base URL: output from `terraform output api_gateway_invoke_url` (e.g. `https://{api-id}.execute-api.us-east-1.amazonaws.com/v1`).

All endpoints return JSON and include CORS headers for browser access from the CloudFront-hosted dashboard.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/recalls` | Paginated list of recalls with optional filters |
| `GET` | `/recalls/stats` | Aggregated statistics across all recalls |
| `GET` | `/recalls/{recall_number}` | Single recall by FDA recall number |
| `OPTIONS` | `*` | CORS preflight (returns 200) |

---

## GET /recalls

Returns a paginated list of recall records from DynamoDB.

### Query parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `classification` | string | No | FDA classification: `Class I`, `Class II`, or `Class III`. When used without `state`, queries the `classification-date-index` GSI. |
| `status` | string | No | Recall status: `Ongoing`, `Completed`, or `Terminated`. |
| `state` | string | No | Two-letter US state code (e.g. `LA`). Filters recalls whose `affected_states` includes this code. Forces a table scan when combined with other filters. |
| `from_date` | string | No | Start date inclusive, `YYYYMMDD` format. |
| `to_date` | string | No | End date inclusive, `YYYYMMDD` format. |
| `limit` | integer | No | Page size. Default `25`, maximum `100`. |
| `next_token` | string | No | Opaque pagination token from a previous response's `next_token` field. |

### Example requests

```bash
# Latest 5 recalls
curl "${API_URL}/recalls?limit=5"

# Class I recalls
curl "${API_URL}/recalls?classification=Class%20I&limit=10"

# Recalls affecting Louisiana
curl "${API_URL}/recalls?state=LA&limit=10"

# Ongoing Class II recalls in a date range
curl "${API_URL}/recalls?classification=Class%20II&status=Ongoing&from_date=20250101&to_date=20250601&limit=25"
```

### Response `200 OK`

```json
{
  "recalls": [
    {
      "PK": "F-1234-2025",
      "SK": "FDA#20250601",
      "classification": "Class I",
      "status": "Ongoing",
      "report_date": "20250601",
      "recall_initiation_date": "20250528",
      "recalling_firm": "Example Foods Inc.",
      "product_description": "Ready-to-eat salad kits",
      "reason_for_recall": "Potential Listeria monocytogenes contamination",
      "distribution_pattern": "Nationwide",
      "affected_states": ["AL", "AK", "..."],
      "is_nationwide": true,
      "firm_city": "Springfield",
      "firm_state": "IL",
      "source": "FDA",
      "ingested_at": "2025-06-01T12:00:00+00:00"
    }
  ],
  "count": 1,
  "next_token": "{\"PK\":{\"S\":\"F-1234-2025\"},\"SK\":{\"S\":\"FDA#20250601\"}}"
}
```

The `next_token` field is present only when more results exist. Pass it unchanged on the next request to fetch the following page.

### Recall object fields

| Field | Type | Description |
|-------|------|-------------|
| `PK` | string | FDA recall number (primary key) |
| `SK` | string | Sort key: `{source}#{report_date}` |
| `classification` | string | `Class I`, `Class II`, or `Class III` |
| `status` | string | `Ongoing`, `Completed`, or `Terminated` |
| `report_date` | string | Date FDA published the report (`YYYYMMDD`) |
| `recall_initiation_date` | string | Date recall was initiated (`YYYYMMDD`) |
| `recalling_firm` | string | Company name |
| `product_description` | string | Product affected |
| `reason_for_recall` | string | FDA-stated reason |
| `distribution_pattern` | string | Raw distribution text from openFDA |
| `affected_states` | string[] | Parsed two-letter state codes |
| `is_nationwide` | boolean | True when distribution covers all US states |
| `firm_city` | string | Recalling firm city |
| `firm_state` | string | Recalling firm state |
| `country` | string | Country (when present) |
| `product_quantity` | string | Quantity description |
| `voluntary_mandated` | string | Voluntary or FDA-mandated |
| `code_info` | string | Lot/batch codes |
| `source` | string | Data source (`FDA` in Phase 1) |
| `ingested_at` | string | ISO 8601 timestamp of last ingestion write |

Empty optional fields may be omitted from DynamoDB items.

---

## GET /recalls/stats

Returns aggregated statistics computed by scanning the full recalls table. Suitable for dashboard map coloring and summary panels.

### Example request

```bash
curl "${API_URL}/recalls/stats"
```

### Response `200 OK`

```json
{
  "total_recalls": 1250,
  "by_classification": {
    "Class I": 120,
    "Class II": 890,
    "Class III": 240
  },
  "by_status": {
    "Ongoing": 45,
    "Completed": 1100,
    "Terminated": 105
  },
  "top_firms": {
    "Example Foods Inc.": 12,
    "Another Brand LLC": 8
  },
  "top_firms_by_severity": [
    {
      "firm": "Example Foods Inc.",
      "severity_score": 18,
      "total_recalls": 8,
      "by_classification": {
        "Class I": 3,
        "Class II": 4,
        "Class III": 1
      }
    }
  ],
  "top_states": {
    "CA": 450,
    "TX": 380,
    "NY": 320
  },
  "state_counts": {
    "AL": 200,
    "AK": 180
  },
  "nationwide_count": 95,
  "nationwide_percentage": 7.6,
  "latest_ingested_at": "2026-06-20T16:30:00+00:00",
  "state_coordinates": {
    "AL": [-86.9023, 32.3182],
    "AK": [-152.4044, 61.3707]
  }
}
```

| Field | Description |
|-------|-------------|
| `total_recalls` | Total items in the table |
| `by_classification` | Count per FDA class |
| `by_status` | Count per recall status |
| `top_firms` | Top 10 recalling firms by recall count |
| `top_firms_by_severity` | Top 10 recalling firms by weighted severity score (`Class I × 3`, `Class II × 2`, `Class III × 1`) |
| `top_states` | Top 10 states by affected-recall count |
| `state_counts` | Full map of state code → recall count |
| `nationwide_count` | Recalls flagged as nationwide distribution |
| `nationwide_percentage` | Percentage of total recalls that are nationwide |
| `latest_ingested_at` | Most recent ingestion timestamp across recalled records |
| `state_coordinates` | Longitude/latitude pairs for map rendering |

---

## GET /recalls/{recall_number}

Returns a single recall record by FDA recall number (the DynamoDB `PK`).

### Path parameters

| Parameter | Description |
|-----------|-------------|
| `recall_number` | FDA recall identifier (e.g. `F-1234-2025`) |

### Example request

```bash
curl "${API_URL}/recalls/F-1234-2025"
```

### Response `200 OK`

Returns a single recall object (same schema as items in `/recalls`).

### Response `404 Not Found`

```json
{
  "error": "Recall not found"
}
```

---

## Error responses

| Status | Body | When |
|--------|------|------|
| `404` | `{"error": "Not found"}` | Unknown path |
| `404` | `{"error": "Recall not found"}` | Unknown recall number |
| `500` | `{"error": "Internal server error"}` | Unhandled Lambda exception |

---

## CORS

All responses include:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

The React dashboard on CloudFront calls this API directly from the browser.

---

## Query behavior notes

- **Classification-only queries** use the `classification-date-index` GSI for efficient reads sorted by `report_date` descending.
- **State filter** requires a table scan because `affected_states` is a list attribute without a dedicated GSI.
- **Stats endpoint** performs a full table scan with projection — acceptable at Phase 1 scale (< ~30K items). See [Future Improvements](../README.md#future-improvements) for the planned precomputed aggregation path.
