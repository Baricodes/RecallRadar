variable "aws_region" {
  description = "AWS region for all RecallRadar resources."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming and tags."
  type        = string
  default     = "recallradar"
}

variable "environment" {
  description = "Deployment environment (e.g. dev, prod)."
  type        = string
  default     = "dev"
}

variable "table_name" {
  description = "DynamoDB table name for recall records."
  type        = string
  default     = "recallradar-recalls"
}

variable "analytics_table_name" {
  description = "DynamoDB table name for Phase 4 analytics records."
  type        = string
  default     = "recallradar-analytics"
}

variable "ingestion_lambda_name" {
  description = "Name of the FDA recall ingestion Lambda function."
  type        = string
  default     = "recallradar-ingestion"
}

variable "ingestion_lookback_days" {
  description = "Number of days to look back when fetching recalls from openFDA."
  type        = number
  default     = 90
}

variable "ingestion_lambda_memory_mb" {
  description = "Memory allocation for the ingestion Lambda (MB)."
  type        = number
  default     = 256
}

variable "ingestion_lambda_timeout_seconds" {
  description = "Timeout for the ingestion Lambda (seconds)."
  type        = number
  default     = 120
}

variable "lambda_source_path" {
  description = "Path to the Lambda package root, relative to terraform/, containing ingestion/, query/, and shared/."
  type        = string
  default     = "../lambda"
}

variable "ingestion_schedule_expression" {
  description = "EventBridge Scheduler expression for ingestion runs."
  type        = string
  default     = "rate(6 hours)"
}

variable "query_lambda_name" {
  description = "Name of the recall query Lambda function."
  type        = string
  default     = "recallradar-query"
}

variable "stream_aggregator_lambda_name" {
  description = "Name of the DynamoDB stream aggregation Lambda function."
  type        = string
  default     = "recallradar-stream-aggregator"
}

variable "trend_compute_lambda_name" {
  description = "Name of the weekly trend computation Lambda function."
  type        = string
  default     = "recallradar-trend-compute"
}

variable "briefing_generator_lambda_name" {
  description = "Name of the weekly Bedrock briefing generator Lambda function."
  type        = string
  default     = "recallradar-briefing-generator"
}

variable "query_lambda_memory_mb" {
  description = "Memory allocation for the query Lambda (MB)."
  type        = number
  default     = 256
}

variable "query_lambda_timeout_seconds" {
  description = "Timeout for the query Lambda (seconds)."
  type        = number
  default     = 30
}

variable "api_name" {
  description = "API Gateway REST API name."
  type        = string
  default     = "recallradar-api"
}

variable "api_stage_name" {
  description = "API Gateway deployment stage."
  type        = string
  default     = "v1"
}

variable "dashboard_bucket_name" {
  description = "S3 bucket name for the React dashboard. Leave empty for recallradar-dashboard-ACCOUNT_ID."
  type        = string
  default     = ""
}

variable "alarm_email" {
  description = "Email for CloudWatch alarm SNS notifications. Leave empty to create the topic without a subscription."
  type        = string
  default     = ""
}

variable "briefing_bucket_name" {
  description = "S3 bucket name for archived weekly briefings. Leave empty for recallradar-briefings-ACCOUNT_ID."
  type        = string
  default     = ""
}

variable "briefing_sender_email" {
  description = "Verified SES sender email for Phase 4 weekly briefings. Leave empty to archive without sending."
  type        = string
  default     = ""
}

variable "briefing_recipient_email" {
  description = "SES recipient email for Phase 4 weekly briefings. Leave empty to archive without sending."
  type        = string
  default     = ""
}

variable "analytics_weekly_schedule_expression" {
  description = "EventBridge schedule expression for the Phase 4 weekly analytics pipeline."
  type        = string
  default     = "cron(0 13 ? * MON *)"
}
