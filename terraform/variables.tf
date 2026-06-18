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

variable "ingestion_lambda_source_path" {
  description = "Path to the ingestion Lambda source directory, relative to the terraform/ directory."
  type        = string
  default     = "../lambda/ingestion"
}
