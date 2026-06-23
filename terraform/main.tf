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
  source_path     = var.lambda_source_path
}

# Phase 1D — EventBridge Scheduler (every 6 hours) + DLQ
module "ingestion_scheduler" {
  source = "./modules/ingestion_scheduler"

  project_name         = var.project_name
  lambda_arn           = module.ingestion_lambda.function_arn
  lambda_function_name = module.ingestion_lambda.function_name
  schedule_expression  = var.ingestion_schedule_expression
}

# Phase 4 — Trend intelligence analytics table, stream aggregation, weekly pipeline
module "analytics" {
  source = "./modules/analytics"

  project_name                     = var.project_name
  analytics_table_name             = var.analytics_table_name
  recalls_table_name               = module.recalls_table.table_name
  recalls_table_arn                = module.recalls_table.table_arn
  recalls_stream_arn               = module.recalls_table.stream_arn
  source_path                      = var.lambda_source_path
  stream_aggregator_function_name  = var.stream_aggregator_lambda_name
  trend_compute_function_name      = var.trend_compute_lambda_name
  briefing_generator_function_name = var.briefing_generator_lambda_name
  briefing_bucket_name             = var.briefing_bucket_name
  briefing_sender_email            = var.briefing_sender_email
  briefing_recipient_email         = var.briefing_recipient_email
  weekly_schedule_expression       = var.analytics_weekly_schedule_expression
}

# Phase 1E — Query Lambda (DynamoDB read API)
module "query_lambda" {
  source = "./modules/query_lambda"

  project_name         = var.project_name
  function_name        = var.query_lambda_name
  table_name           = module.recalls_table.table_name
  table_arn            = module.recalls_table.table_arn
  analytics_table_name = module.analytics.analytics_table_name
  analytics_table_arn  = module.analytics.analytics_table_arn
  memory_mb            = var.query_lambda_memory_mb
  timeout_seconds      = var.query_lambda_timeout_seconds
  source_path          = var.lambda_source_path
}

# Phase 1E — API Gateway REST API
module "api_gateway" {
  source = "./modules/api_gateway"

  api_name             = var.api_name
  stage_name           = var.api_stage_name
  lambda_invoke_arn    = module.query_lambda.invoke_arn
  lambda_function_name = module.query_lambda.function_name
}

# Phase 1G — S3 + CloudFront dashboard hosting
module "dashboard_hosting" {
  source = "./modules/dashboard_hosting"

  project_name              = var.project_name
  bucket_name               = var.dashboard_bucket_name
  api_gateway_domain_name   = module.api_gateway.domain_name
  api_gateway_stage_name    = module.api_gateway.stage_name
  api_gateway_api_key_value = module.api_gateway.cloudfront_api_key_value
}

# Phase 1H — CloudWatch dashboard and alarms
module "monitoring" {
  source = "./modules/monitoring"

  project_name          = var.project_name
  aws_region            = var.aws_region
  ingestion_lambda_name = module.ingestion_lambda.function_name
  dynamodb_table_name   = module.recalls_table.table_name
  api_name              = var.api_name
  api_stage_name        = var.api_stage_name
  dlq_name              = "${var.project_name}-dlq"
  alarm_email           = var.alarm_email
}
