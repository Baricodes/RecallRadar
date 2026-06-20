variable "api_name" {
  description = "Name of the REST API."
  type        = string
}

variable "stage_name" {
  description = "API Gateway deployment stage name."
  type        = string
  default     = "v1"
}

variable "lambda_invoke_arn" {
  description = "Invoke ARN of the query Lambda."
  type        = string
}

variable "lambda_function_name" {
  description = "Name of the query Lambda function."
  type        = string
}

variable "throttle_rate_limit" {
  description = "Steady-state requests per second allowed for the CloudFront API key."
  type        = number
  default     = 10
}

variable "throttle_burst_limit" {
  description = "Short burst request limit allowed for the CloudFront API key."
  type        = number
  default     = 20
}
