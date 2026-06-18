# Phase 1A — DynamoDB table with GSIs for recall queries
module "recalls_table" {
  source = "./modules/recalls_table"

  table_name = var.table_name
}

# Phase 1B — Ingestion Lambda (openFDA → DynamoDB)
module "ingestion_lambda" {
  source = "./modules/ingestion_lambda"

  project_name    = var.project_name
  function_name   = var.ingestion_lambda_name
  table_name      = module.recalls_table.table_name
  table_arn       = module.recalls_table.table_arn
  lookback_days   = var.ingestion_lookback_days
  memory_mb       = var.ingestion_lambda_memory_mb
  timeout_seconds = var.ingestion_lambda_timeout_seconds
  source_path     = var.ingestion_lambda_source_path
}
