variable "project_name" {
  description = "Project name used for resource naming."
  type        = string
}

variable "analytics_table_name" {
  description = "DynamoDB table name for precomputed analytics records."
  type        = string
}

variable "recalls_table_name" {
  description = "DynamoDB table name for normalized recall records."
  type        = string
}

variable "recalls_table_arn" {
  description = "ARN of the recalls DynamoDB table."
  type        = string
}

variable "recalls_stream_arn" {
  description = "ARN of the recalls DynamoDB stream."
  type        = string
}

variable "source_path" {
  description = "Path to the Lambda package root, relative to terraform/."
  type        = string
}

variable "stream_aggregator_function_name" {
  description = "Name of the DynamoDB stream aggregation Lambda."
  type        = string
}

variable "trend_compute_function_name" {
  description = "Name of the weekly trend computation Lambda."
  type        = string
}

variable "briefing_generator_function_name" {
  description = "Name of the Bedrock weekly briefing Lambda."
  type        = string
}

variable "briefing_bucket_name" {
  description = "S3 bucket name for weekly briefing archives. Leave empty for recallradar-briefings-ACCOUNT_ID."
  type        = string
  default     = ""
}

variable "briefing_sender_email" {
  description = "Verified SES sender email for weekly briefings. Leave empty to archive without sending."
  type        = string
  default     = ""
}

variable "briefing_recipient_email" {
  description = "SES recipient email for weekly briefings. Leave empty to archive without sending."
  type        = string
  default     = ""
}

variable "weekly_schedule_expression" {
  description = "EventBridge schedule for the weekly analytics pipeline."
  type        = string
}
