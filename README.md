# RecallRadar

> A real-time recall intelligence platform that ingests FDA food recall data, maps geographic impact across the United States, and surfaces insights about recall severity, frequency, and trends that nobody else aggregates.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)
![AWS Lambda](https://img.shields.io/badge/AWS_Lambda-FF9900?style=flat&logo=amazon-aws&logoColor=white)
![DynamoDB](https://img.shields.io/badge/DynamoDB-4053D6?style=flat&logo=amazon-dynamodb&logoColor=white)
![API Gateway](https://img.shields.io/badge/API_Gateway-FF4F8B?style=flat&logo=amazon-api-gateway&logoColor=white)
![CloudFront](https://img.shields.io/badge/CloudFront-8C4FFF?style=flat&logo=amazon-aws&logoColor=white)
![EventBridge](https://img.shields.io/badge/EventBridge-FF4F8B?style=flat&logo=amazon-aws&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=flat&logo=terraform&logoColor=white)

## Demo

<!-- Add dashboard-demo.gif after capturing — see images/README.md -->
<!-- ![Dashboard demo](./images/dashboard-demo.gif) -->

Live dashboard URL: run `terraform output cloudfront_url` after deploy.

## Architecture

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
│  GSI: classification,   │
│       source, status    │
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
│  recallradar-*.cloud    │       │                      │
│  front.net              │       │  index.html          │
└─────────────────────────┘       │  static/js/          │
                                  │  static/css/         │
        Dashboard features:       └──────────────────────┘
        • Interactive US state map (color-coded by recall volume)
        • Live recall feed with severity badges
        • Stats panel (total active, by classification, top firms)
        • Filter by state, classification, status
```

## How it works

1. **Scheduled ingestion** — EventBridge Scheduler invokes the ingestion Lambda every 6 hours (with a 15-minute flexible window). Failed invocations land in an SQS dead-letter queue.

2. **openFDA fetch** — The Lambda paginates through the [openFDA food enforcement API](https://open.fda.gov/apis/food/enforcement/), requesting recalls within a configurable lookback window (default 90 days).

3. **Normalize and parse** — Each record is normalized to a DynamoDB item. The free-text `distribution_pattern` field is parsed with regex into structured `affected_states` and an `is_nationwide` flag. Individual write failures are logged without aborting the batch.

4. **Idempotent storage** — Records are keyed by FDA `recall_number` (PK) and `source#report_date` (SK). Re-running ingestion overwrites existing items — no duplicates.

5. **Query API** — API Gateway routes GET requests to the query Lambda, which reads from DynamoDB with GSI-backed queries (classification) or scans (state filter, stats).

6. **Dashboard** — A React app on CloudFront calls the API from the browser. The map colors states by recall volume; clicking a state filters the feed. A stats panel shows classification breakdowns and top recalling firms.

7. **Monitoring** — A CloudWatch dashboard tracks Lambda invocations, errors, duration, DynamoDB capacity, API 5xx, and DLQ depth. SNS alarms fire on ingestion errors and DLQ messages.

## Key design decisions

| Decision | Why |
|----------|-----|
| `recall_number` as DynamoDB PK | Natural idempotency — re-running ingestion never creates duplicates. Same pattern as stateful deduplication in production alert systems. |
| On-demand DynamoDB capacity | Write pattern is bursty (batch after each API poll) with long idle periods between. Provisioned capacity would waste money on a system that writes once every 6 hours. |
| 6-hour polling instead of continuous | openFDA updates weekly. Polling every 15 min = 672 invocations to catch 1 update. 6 hours = 28 invocations. Operational efficiency over aggressive freshness. |
| OAC over public S3 bucket | CloudFront Origin Access Control keeps the S3 bucket private. The dashboard is served through the CDN only — no public bucket policy. |
| State parsing as a Python function, not Bedrock | `distribution_pattern` has limited patterns — regex handles 95% of cases. Calling Bedrock for string parsing at ingestion time adds cost and latency that isn't justified. AI enrichment targets higher-value analysis like risk scoring. |
| Scan for stats endpoint (Phase 1) | Full table scan is acceptable when the table has < 30K items and the stats endpoint is called infrequently. DynamoDB Streams + precomputed aggregations replace this before scale matters. |

## Screenshots

Capture instructions are in [`images/README.md`](./images/README.md).

| Asset | Description |
|-------|-------------|
| Dashboard GIF | Map + feed + filters in action |
| CloudWatch dashboard | 24h+ healthy operation metrics |
| DynamoDB table | Populated recall items |
| EventBridge schedule | 6-hour ingestion trigger |
| API Gateway resources | `/recalls` route tree |

<!-- Uncomment after capturing assets:
![Dashboard demo](./images/dashboard-demo.gif)
![CloudWatch dashboard](./images/cloudwatch-dashboard.png)
-->

## Project structure

```
RecallRadar/
├── lambda/
│   ├── ingestion/          openFDA → DynamoDB ingestion handler
│   ├── query/              API query handler
│   ├── shared/             State parsing + geocoding constants
│   └── tests/              Unit tests for state parsing
├── dashboard/
│   ├── src/components/     RecallMap, RecallFeed, StatsPanel, FilterBar
│   └── src/App.js          Main dashboard layout
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   └── modules/
│       ├── recalls_table/
│       ├── ingestion_lambda/
│       ├── ingestion_scheduler/
│       ├── query_lambda/
│       ├── api_gateway/
│       ├── dashboard_hosting/
│       └── monitoring/
├── scripts/
│   └── deploy-dashboard.sh Build and sync dashboard to S3 + CloudFront
├── docs/
│   └── API.md              REST API reference
├── images/                 Portfolio screenshots and demo GIFs
└── README.md
```

## Prerequisites

- [Terraform](https://www.terraform.io/downloads) >= 1.5
- [AWS CLI](https://aws.amazon.com/cli/) configured with credentials for `us-east-1`
- [Node.js](https://nodejs.org/) 18+ (dashboard build)
- Python 3.12+ (local Lambda development and tests)

## Deploy

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # optional: customize variables
terraform init
terraform plan
terraform apply
```

After apply, Terraform prints the DynamoDB table name, API invoke URL, CloudFront dashboard URL, and example curl commands.

Set `alarm_email` in `terraform.tfvars` to receive CloudWatch alarm notifications (confirm the SNS subscription in your inbox).

### Deploy the dashboard

```bash
chmod +x scripts/deploy-dashboard.sh
./scripts/deploy-dashboard.sh
```

Or run the one-liner from `terraform output dashboard_deploy_command`.

For local development:

```bash
cd dashboard
cp .env.example .env.local   # set REACT_APP_API_URL to your API Gateway URL
npm install
npm start
```

### Manual ingestion test

```bash
aws lambda invoke \
  --function-name recallradar-ingestion \
  --payload '{}' \
  /tmp/recallradar-ingestion-response.json

cat /tmp/recallradar-ingestion-response.json
```

### API test

```bash
# Replace with api_gateway_invoke_url from terraform output
curl "$(terraform -chdir=terraform output -raw api_gateway_invoke_url)/recalls?limit=5"
curl "$(terraform -chdir=terraform output -raw api_gateway_invoke_url)/recalls/stats"
```

Full API documentation: [`docs/API.md`](./docs/API.md).

## Local tests

```bash
python -m pytest lambda/tests/ -v
```

## Configuration

Key Terraform variables (see `terraform/variables.tf`):

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-1` | AWS region for all resources |
| `table_name` | `recallradar-recalls` | DynamoDB table name |
| `ingestion_lookback_days` | `90` | Days of recall history to fetch from openFDA |
| `ingestion_schedule_expression` | `rate(6 hours)` | How often ingestion runs |
| `api_stage_name` | `v1` | API Gateway deployment stage |
| `alarm_email` | `""` | SNS email for CloudWatch alarms |

## Cost

Phase 1 runs for approximately **$3/month** — mostly CloudWatch dashboard and alarms. Lambda, DynamoDB, API Gateway, EventBridge, S3, and CloudFront stay within free tier at typical usage.

| Service | Usage | Monthly cost |
|---------|-------|--------------|
| Lambda (ingestion + query) | ~120 + ~1000 invocations | Free tier |
| DynamoDB (on-demand) | ~30K items | Free tier |
| API Gateway | ~1000 requests | Free tier |
| EventBridge Scheduler | 4 invocations/day | Free tier |
| S3 + CloudFront | Static dashboard | ~$0.01 |
| CloudWatch | Dashboard + 2 alarms | ~$3.00 |

## Future improvements

Planned extensions that layer on top of Phase 1 without refactoring the core pipeline:

- **Phase 2 — AI enrichment** — Bedrock analyzes `reason_for_recall` for plain-English risk summaries and severity scores
- **Phase 3 — Multi-source** — CPSC, NHTSA, and USDA adapters using the same ingestion pattern
- **Phase 4 — Trend intelligence** — Timestream for time-series analytics and precomputed stats (replaces full-table scan)
- **Phase 5 — User subscriptions** — Cognito auth + SNS/SES alerts when recalls match user location and allergen profile
- **Phase 6 — Predictive analytics** — Correlate recall patterns with FDA inspection data
- **Real-time feed** — WebSocket API for live dashboard updates without polling

## Data source

Recall data comes from the [openFDA food enforcement API](https://open.fda.gov/apis/food/enforcement/). FDA classifications:

- **Class I** — Dangerous or defective product that could cause serious health problems or death
- **Class II** — Product may cause temporary or medically reversible health problems
- **Class III** — Product unlikely to cause adverse health consequences
