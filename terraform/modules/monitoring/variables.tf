variable "project_name" {
  description = "Project name used for resource naming."
  type        = string
}

variable "aws_region" {
  description = "AWS region for dashboard widgets."
  type        = string
  default     = "us-east-1"
}

variable "ingestion_lambda_name" {
  description = "Name of the ingestion Lambda function."
  type        = string
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB recalls table."
  type        = string
}

variable "api_name" {
  description = "API Gateway REST API name."
  type        = string
}

variable "api_stage_name" {
  description = "API Gateway deployment stage."
  type        = string
}

variable "dlq_name" {
  description = "SQS dead-letter queue name."
  type        = string
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarm notifications. Leave empty to skip subscription."
  type        = string
  default     = ""
}
