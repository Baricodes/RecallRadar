# RecallRadar

RecallRadar monitors FDA food recall enforcement data and stores it in AWS for querying and alerting. Phase 1 focuses on infrastructure: a DynamoDB table and a scheduled ingestion Lambda that pulls recent recalls from the [openFDA API](https://open.fda.gov/apis/food/enforcement/).

## Architecture

```
openFDA API  →  Ingestion Lambda  →  DynamoDB (recalls table)
```

- **DynamoDB** — Single-table design with GSIs for classification, source, status, and report date queries.
- **Ingestion Lambda** — Fetches food enforcement reports, normalizes records, and writes them idempotently to DynamoDB.

## Project structure

```
lambda/ingestion/     Python Lambda handler and dependencies
terraform/            Root module and reusable Terraform modules
  modules/recalls_table/
  modules/ingestion_lambda/
```

## Prerequisites

- [Terraform](https://www.terraform.io/downloads) >= 1.5
- [AWS CLI](https://aws.amazon.com/cli/) configured with credentials for `us-east-1`
- Python 3.12+ (for local Lambda development)

## Deploy

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # optional: customize variables
terraform init
terraform plan
terraform apply
```

After apply, Terraform prints the table name, Lambda ARN, and a CLI command to invoke ingestion manually.

### Manual ingestion test

```bash
aws lambda invoke \
  --function-name recallradar-ingestion \
  --payload '{}' \
  /tmp/recallradar-ingestion-response.json

cat /tmp/recallradar-ingestion-response.json
```

## Configuration

Key variables (see `terraform/variables.tf`):

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-1` | AWS region for all resources |
| `table_name` | `recallradar-recalls` | DynamoDB table name |
| `ingestion_lookback_days` | `90` | Days of recall history to fetch from openFDA |
