variable "project_name" {
  description = "Project name used for resource naming."
  type        = string
}

variable "bucket_name" {
  description = "S3 bucket name for dashboard static files. Defaults to recallradar-dashboard-ACCOUNT_ID."
  type        = string
  default     = ""
}

variable "price_class" {
  description = "CloudFront price class."
  type        = string
  default     = "PriceClass_100"
}

variable "api_gateway_domain_name" {
  description = "API Gateway domain name for CloudFront /api routing."
  type        = string
}

variable "api_gateway_stage_name" {
  description = "API Gateway stage name used as the CloudFront API origin path."
  type        = string
}

variable "api_gateway_api_key_value" {
  description = "API key value CloudFront sends to API Gateway."
  type        = string
  sensitive   = true
}
