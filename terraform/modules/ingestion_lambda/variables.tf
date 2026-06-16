variable "project_name" {
  description = "Project name used for IAM resource naming."
  type        = string
}

variable "function_name" {
  description = "Lambda function name."
  type        = string
}

variable "table_name" {
  description = "DynamoDB table name the Lambda writes to."
  type        = string
}

variable "table_arn" {
  description = "DynamoDB table ARN the Lambda writes to."
  type        = string
}

variable "lookback_days" {
  description = "Days to look back when fetching recalls from openFDA."
  type        = number
}

variable "memory_mb" {
  description = "Lambda memory in MB."
  type        = number
}

variable "timeout_seconds" {
  description = "Lambda timeout in seconds."
  type        = number
}

variable "source_path" {
  description = "Path to Lambda source directory containing handler.py."
  type        = string
}
