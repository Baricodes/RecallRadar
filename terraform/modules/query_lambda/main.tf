data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  lambda_root = abspath("${path.root}/${var.source_path}")
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = local.lambda_root
  output_path = "${path.module}/.build/${var.function_name}.zip"

  excludes = [
    "ingestion",
    "tests",
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
  ]
}

resource "aws_iam_role" "query" {
  name = "${var.project_name}-query-role"

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

resource "aws_iam_role_policy" "query" {
  name = "${var.project_name}-query-policy"
  role = aws_iam_role.query.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBRead"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          var.table_arn,
          "${var.table_arn}/index/*",
          var.analytics_table_arn,
          "${var.analytics_table_arn}/index/*"
        ]
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

resource "aws_cloudwatch_log_group" "query" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = 14
}

resource "aws_lambda_function" "query" {
  function_name = var.function_name
  role          = aws_iam_role.query.arn
  handler       = "query.handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  memory_size = var.memory_mb
  timeout     = var.timeout_seconds

  environment {
    variables = {
      TABLE_NAME      = var.table_name
      ANALYTICS_TABLE = var.analytics_table_name
    }
  }

  depends_on = [
    aws_iam_role_policy.query,
    aws_cloudwatch_log_group.query
  ]
}
