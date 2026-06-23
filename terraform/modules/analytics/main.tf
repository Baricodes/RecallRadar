data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  lambda_root      = abspath("${path.root}/${var.source_path}")
  briefing_bucket  = var.briefing_bucket_name != "" ? var.briefing_bucket_name : "${var.project_name}-briefings-${data.aws_caller_identity.current.account_id}"
  common_excludes  = ["tests", "__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache", ".ruff_cache"]
  analytics_policy = [aws_dynamodb_table.analytics.arn]
}

resource "aws_dynamodb_table" "analytics" {
  name         = var.analytics_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }
}

resource "aws_s3_bucket" "briefings" {
  bucket = local.briefing_bucket
}

resource "aws_s3_bucket_public_access_block" "briefings" {
  bucket = aws_s3_bucket.briefings.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "briefings" {
  bucket = aws_s3_bucket.briefings.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

data "archive_file" "stream_aggregator_zip" {
  type        = "zip"
  source_dir  = local.lambda_root
  output_path = "${path.module}/.build/${var.stream_aggregator_function_name}.zip"

  excludes = concat(local.common_excludes, [
    "briefing_generator",
    "ingestion",
    "query",
    "trend_compute",
  ])
}

data "archive_file" "trend_compute_zip" {
  type        = "zip"
  source_dir  = local.lambda_root
  output_path = "${path.module}/.build/${var.trend_compute_function_name}.zip"

  excludes = concat(local.common_excludes, [
    "briefing_generator",
    "ingestion",
    "query",
    "stream_aggregator",
  ])
}

data "archive_file" "briefing_generator_zip" {
  type        = "zip"
  source_dir  = local.lambda_root
  output_path = "${path.module}/.build/${var.briefing_generator_function_name}.zip"

  excludes = concat(local.common_excludes, [
    "ingestion",
    "query",
    "stream_aggregator",
    "trend_compute",
  ])
}

resource "aws_iam_role" "stream_aggregator" {
  name = "${var.project_name}-stream-aggregator-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "stream_aggregator" {
  name = "${var.project_name}-stream-aggregator-policy"
  role = aws_iam_role.stream_aggregator.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadRecallStream"
        Effect = "Allow"
        Action = [
          "dynamodb:DescribeStream",
          "dynamodb:GetRecords",
          "dynamodb:GetShardIterator",
          "dynamodb:ListStreams"
        ]
        Resource = var.recalls_stream_arn
      },
      {
        Sid    = "WriteAnalytics"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.analytics.arn
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

resource "aws_cloudwatch_log_group" "stream_aggregator" {
  name              = "/aws/lambda/${var.stream_aggregator_function_name}"
  retention_in_days = 14
}

resource "aws_lambda_function" "stream_aggregator" {
  function_name = var.stream_aggregator_function_name
  role          = aws_iam_role.stream_aggregator.arn
  handler       = "stream_aggregator.handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]

  filename         = data.archive_file.stream_aggregator_zip.output_path
  source_code_hash = data.archive_file.stream_aggregator_zip.output_base64sha256

  memory_size = 256
  timeout     = 60

  environment {
    variables = {
      ANALYTICS_TABLE = aws_dynamodb_table.analytics.name
    }
  }

  depends_on = [
    aws_iam_role_policy.stream_aggregator,
    aws_cloudwatch_log_group.stream_aggregator
  ]
}

resource "aws_lambda_event_source_mapping" "recalls_stream" {
  event_source_arn                   = var.recalls_stream_arn
  function_name                      = aws_lambda_function.stream_aggregator.arn
  starting_position                  = "LATEST"
  batch_size                         = 25
  maximum_batching_window_in_seconds = 30
  bisect_batch_on_function_error     = true
  maximum_retry_attempts             = 3

  filter_criteria {
    filter {
      pattern = jsonencode({
        eventName = ["INSERT"]
      })
    }
  }
}

resource "aws_iam_role" "trend_compute" {
  name = "${var.project_name}-trend-compute-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "trend_compute" {
  name = "${var.project_name}-trend-compute-policy"
  role = aws_iam_role.trend_compute.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadRecalls"
        Effect = "Allow"
        Action = [
          "dynamodb:Scan",
          "dynamodb:Query"
        ]
        Resource = [
          var.recalls_table_arn,
          "${var.recalls_table_arn}/index/*"
        ]
      },
      {
        Sid    = "WriteAnalytics"
        Effect = "Allow"
        Action = [
          "dynamodb:BatchWriteItem",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.analytics.arn
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

resource "aws_cloudwatch_log_group" "trend_compute" {
  name              = "/aws/lambda/${var.trend_compute_function_name}"
  retention_in_days = 14
}

resource "aws_lambda_function" "trend_compute" {
  function_name = var.trend_compute_function_name
  role          = aws_iam_role.trend_compute.arn
  handler       = "trend_compute.handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]

  filename         = data.archive_file.trend_compute_zip.output_path
  source_code_hash = data.archive_file.trend_compute_zip.output_base64sha256

  memory_size = 512
  timeout     = 300

  environment {
    variables = {
      ANALYTICS_TABLE = aws_dynamodb_table.analytics.name
      RECALLS_TABLE   = var.recalls_table_name
    }
  }

  depends_on = [
    aws_iam_role_policy.trend_compute,
    aws_cloudwatch_log_group.trend_compute
  ]
}

resource "aws_iam_role" "briefing_generator" {
  name = "${var.project_name}-briefing-generator-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "briefing_generator" {
  name = "${var.project_name}-briefing-generator-policy"
  role = aws_iam_role.briefing_generator.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadWriteAnalytics"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.analytics.arn
      },
      {
        Sid    = "ArchiveBriefings"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject"
        ]
        Resource = [
          aws_s3_bucket.briefings.arn,
          "${aws_s3_bucket.briefings.arn}/*"
        ]
      },
      {
        Sid      = "InvokeBedrock"
        Effect   = "Allow"
        Action   = "bedrock:InvokeModel"
        Resource = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
      },
      {
        Sid    = "SendBriefingEmail"
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
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

resource "aws_cloudwatch_log_group" "briefing_generator" {
  name              = "/aws/lambda/${var.briefing_generator_function_name}"
  retention_in_days = 14
}

resource "aws_lambda_function" "briefing_generator" {
  function_name = var.briefing_generator_function_name
  role          = aws_iam_role.briefing_generator.arn
  handler       = "briefing_generator.handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]

  filename         = data.archive_file.briefing_generator_zip.output_path
  source_code_hash = data.archive_file.briefing_generator_zip.output_base64sha256

  memory_size = 512
  timeout     = 120

  environment {
    variables = {
      ANALYTICS_TABLE = aws_dynamodb_table.analytics.name
      BRIEFING_BUCKET = aws_s3_bucket.briefings.bucket
      RECIPIENT_EMAIL = var.briefing_recipient_email
      SENDER_EMAIL    = var.briefing_sender_email
    }
  }

  depends_on = [
    aws_iam_role_policy.briefing_generator,
    aws_cloudwatch_log_group.briefing_generator
  ]
}

resource "aws_iam_role" "weekly_analytics" {
  name = "${var.project_name}-weekly-analytics-sfn-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "states.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "weekly_analytics" {
  name = "${var.project_name}-weekly-analytics-sfn-policy"
  role = aws_iam_role.weekly_analytics.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "lambda:InvokeFunction"
      Resource = [
        aws_lambda_function.trend_compute.arn,
        aws_lambda_function.briefing_generator.arn
      ]
    }]
  })
}

resource "aws_sfn_state_machine" "weekly_analytics" {
  name     = "${var.project_name}-weekly-analytics"
  role_arn = aws_iam_role.weekly_analytics.arn

  definition = jsonencode({
    Comment = "RecallRadar Phase 4 weekly trend analytics pipeline"
    StartAt = "ComputeTrends"
    States = {
      ComputeTrends = {
        Type       = "Task"
        Resource   = aws_lambda_function.trend_compute.arn
        ResultPath = "$.trend_results"
        Retry = [{
          ErrorEquals = ["States.ALL"]
          MaxAttempts = 2
          BackoffRate = 2
        }]
        Next = "GenerateBriefing"
      }
      GenerateBriefing = {
        Type       = "Task"
        Resource   = aws_lambda_function.briefing_generator.arn
        ResultPath = "$.briefing_result"
        Retry = [{
          ErrorEquals = ["States.ALL"]
          MaxAttempts = 1
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "BriefingFailed"
          ResultPath  = "$.error"
        }]
        End = true
      }
      BriefingFailed = {
        Type = "Pass"
        Result = {
          status = "BRIEFING_FAILED"
        }
        End = true
      }
    }
  })
}

resource "aws_iam_role" "weekly_schedule" {
  name = "${var.project_name}-weekly-analytics-events-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "weekly_schedule" {
  name = "${var.project_name}-weekly-analytics-events-policy"
  role = aws_iam_role.weekly_schedule.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "states:StartExecution"
      Resource = aws_sfn_state_machine.weekly_analytics.arn
    }]
  })
}

resource "aws_cloudwatch_event_rule" "weekly_analytics" {
  name                = "${var.project_name}-weekly-analytics"
  description         = "Starts the RecallRadar Phase 4 weekly analytics pipeline."
  schedule_expression = var.weekly_schedule_expression
}

resource "aws_cloudwatch_event_target" "weekly_analytics" {
  rule     = aws_cloudwatch_event_rule.weekly_analytics.name
  arn      = aws_sfn_state_machine.weekly_analytics.arn
  role_arn = aws_iam_role.weekly_schedule.arn
}
