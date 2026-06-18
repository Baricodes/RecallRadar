variable "project_name" {
  description = "Project name used for IAM resource naming."
  type        = string
}

variable "function_name" {
  description = "Lambda function name."
  type        = string
}

variable "table_name" {
  description = "DynamoDB table name the Lambda reads from."
  type        = string
}

variable "table_arn" {
  description = "DynamoDB table ARN the Lambda reads from."
  type        = string
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
  description = "Path to the Lambda package root (relative to terraform root), containing query/ and shared/."
  type        = string
  default     = "../lambda"
}
