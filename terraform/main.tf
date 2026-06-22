# Phase 1A — DynamoDB table with GSIs for recall queries
module "recalls_table" {
  source = "./modules/recalls_table"

  table_name = var.table_name
}

locals {
  phase3_sources = {
    FDA_FOOD   = "recallradar-fda-food-ingestion"
    FDA_DRUG   = "recallradar-fda-drug-ingestion"
    FDA_DEVICE = "recallradar-fda-device-ingestion"
    CPSC       = "recallradar-cpsc-ingestion"
    USDA       = "recallradar-usda-ingestion"
    NHTSA      = "recallradar-nhtsa-ingestion"
  }
}

# Phase 3 — Source-specific ingestion Lambdas (fanned out by Step Functions)
module "ingestion_lambda" {
  for_each = local.phase3_sources

  source = "./modules/ingestion_lambda"

  project_name    = var.project_name
  function_name   = each.value
  table_name      = module.recalls_table.table_name
  table_arn       = module.recalls_table.table_arn
  lookback_days   = var.ingestion_lookback_days
  source_name     = each.key
  memory_mb       = var.ingestion_lambda_memory_mb
  timeout_seconds = var.ingestion_lambda_timeout_seconds
  source_path     = var.lambda_source_path
}

resource "aws_iam_role" "recall_ingestion_state_machine" {
  name = "${var.project_name}-phase3-ingestion-sfn-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "recall_ingestion_state_machine" {
  name = "${var.project_name}-phase3-ingestion-sfn-policy"
  role = aws_iam_role.recall_ingestion_state_machine.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = [for source, module_instance in module.ingestion_lambda : module_instance.function_arn]
      }
    ]
  })
}

resource "aws_sfn_state_machine" "recall_ingestion" {
  name     = "${var.project_name}-phase3-ingestion"
  role_arn = aws_iam_role.recall_ingestion_state_machine.arn

  definition = jsonencode({
    Comment = "RecallRadar Phase 3 multi-source ingestion orchestrator"
    StartAt = "ParallelIngestion"
    States = {
      ParallelIngestion = {
        Type = "Parallel"
        Branches = [
          for source, module_instance in module.ingestion_lambda : {
            StartAt = "Ingest${replace(source, "_", "")}"
            States = {
              "Ingest${replace(source, "_", "")}" = {
                Type       = "Task"
                Resource   = module_instance.function_arn
                ResultPath = "$.${lower(source)}_result"
                Retry = [
                  {
                    ErrorEquals = ["States.ALL"]
                    MaxAttempts = 2
                    BackoffRate = 2
                  }
                ]
                Catch = [
                  {
                    ErrorEquals = ["States.ALL"]
                    Next        = "${replace(source, "_", "")}Failed"
                  }
                ]
                End = true
              }
              "${replace(source, "_", "")}Failed" = {
                Type   = "Pass"
                Result = { source = source, status = "FAILED" }
                End    = true
              }
            }
          }
        ]
        End = true
      }
    }
  })
}

# Phase 3 — EventBridge Scheduler (every 6 hours) + DLQ
module "ingestion_scheduler" {
  source = "./modules/ingestion_scheduler"

  project_name         = var.project_name
  lambda_arn           = aws_sfn_state_machine.recall_ingestion.arn
  lambda_function_name = ""
  target_type          = "state_machine"
  schedule_expression  = var.ingestion_schedule_expression
}

# Phase 1E — Query Lambda (DynamoDB read API)
module "query_lambda" {
  source = "./modules/query_lambda"

  project_name    = var.project_name
  function_name   = var.query_lambda_name
  table_name      = module.recalls_table.table_name
  table_arn       = module.recalls_table.table_arn
  memory_mb       = var.query_lambda_memory_mb
  timeout_seconds = var.query_lambda_timeout_seconds
  source_path     = var.lambda_source_path
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
  ingestion_lambda_name = module.ingestion_lambda["FDA_FOOD"].function_name
  dynamodb_table_name   = module.recalls_table.table_name
  api_name              = var.api_name
  api_stage_name        = var.api_stage_name
  dlq_name              = "${var.project_name}-dlq"
  alarm_email           = var.alarm_email
}
