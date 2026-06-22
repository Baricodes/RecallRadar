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

variable "source_name" {
  description = "Recall source this Lambda ingests, such as FDA_FOOD or CPSC."
  type        = string
  default     = "FDA_FOOD"
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
  description = "Path to the Lambda package root (relative to terraform root), containing ingestion/ and shared/."
  type        = string
  default     = "../lambda"
}
