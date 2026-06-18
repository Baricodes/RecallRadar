variable "project_name" {
  description = "Project name used for resource naming."
  type        = string
}

variable "lambda_arn" {
  description = "ARN of the ingestion Lambda to invoke."
  type        = string
}

variable "lambda_function_name" {
  description = "Name of the ingestion Lambda (for invoke permission)."
  type        = string
}

variable "schedule_expression" {
  description = "EventBridge Scheduler expression (e.g. rate(6 hours))."
  type        = string
  default     = "rate(6 hours)"
}

variable "flexible_window_minutes" {
  description = "Flexible time window in minutes to spread schedule invocations."
  type        = number
  default     = 15
}

variable "max_retry_attempts" {
  description = "Maximum retry attempts for failed schedule invocations."
  type        = number
  default     = 2
}

variable "max_event_age_seconds" {
  description = "Maximum age in seconds for a scheduled event before it is discarded."
  type        = number
  default     = 3600
}
