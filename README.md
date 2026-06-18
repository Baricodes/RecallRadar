# RecallRadar

RecallRadar monitors FDA food recall enforcement data and stores it in AWS for querying and visualization. Phase 1 builds a full data pipeline: scheduled ingestion, DynamoDB storage, and a REST API for the dashboard.

## Architecture

```
EventBridge Scheduler (every 6 hours)
        │
        ▼
openFDA API  →  Ingestion Lambda  →  DynamoDB (recalls table)
                                           ▲
                                           │
                              Query Lambda ← API Gateway (REST)
```

- **DynamoDB** — Single-table design with GSIs for classification, source, status, and report date queries.
- **Ingestion Lambda** — Fetches food enforcement reports, parses affected states, and writes idempotently to DynamoDB.
- **EventBridge Scheduler** — Triggers ingestion every 6 hours with a 15-minute flexible window and SQS dead-letter queue.
- **Query Lambda + API Gateway** — REST endpoints for paginated recalls, stats, and single-recall detail.

## Project structure

```
lambda/
  ingestion/          FDA recall ingestion handler
  query/              API query handler
  shared/             State parsing + geocoding constants
  tests/              Unit tests for state parsing
terraform/
  modules/
    recalls_table/
    ingestion_lambda/
    ingestion_scheduler/
    query_lambda/
    api_gateway/
```

## Prerequisites

- [Terraform](https://www.terraform.io/downloads) >= 1.5
- [AWS CLI](https://aws.amazon.com/cli/) configured with credentials for `us-east-1`
- Python 3.12+ (for local Lambda development and tests)

## Deploy

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # optional: customize variables
terraform init
terraform plan
terraform apply
```

After apply, Terraform prints the DynamoDB table name, API invoke URL, and example curl commands.

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
curl "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/v1/recalls?limit=5"
curl "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/v1/recalls/stats"
```

## Local tests

```bash
python -m pytest lambda/tests/ -v
```

## Configuration

Key variables (see `terraform/variables.tf`):

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-1` | AWS region for all resources |
| `table_name` | `recallradar-recalls` | DynamoDB table name |
| `ingestion_lookback_days` | `90` | Days of recall history to fetch from openFDA |
| `ingestion_schedule_expression` | `rate(6 hours)` | How often ingestion runs |
| `api_stage_name` | `v1` | API Gateway deployment stage |
