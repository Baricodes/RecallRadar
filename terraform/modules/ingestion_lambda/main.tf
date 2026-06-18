data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  source_dir = abspath("${path.root}/${var.source_path}")
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = local.source_dir
  output_path = "${path.module}/.build/${var.function_name}.zip"

  excludes = [
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
  ]
}

resource "aws_iam_role" "ingestion" {
  name = "${var.project_name}-ingestion-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "ingestion" {
  name = "${var.project_name}-ingestion-policy"
  role = aws_iam_role.ingestion.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBWrite"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = var.table_arn
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "ingestion" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = 14
}

resource "aws_lambda_function" "ingestion" {
  function_name = var.function_name
  role          = aws_iam_role.ingestion.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  memory_size = var.memory_mb
  timeout     = var.timeout_seconds

  environment {
    variables = {
      TABLE_NAME    = var.table_name
      LOOKBACK_DAYS = tostring(var.lookback_days)
    }
  }

  depends_on = [
    aws_iam_role_policy.ingestion,
    aws_cloudwatch_log_group.ingestion
  ]
}
