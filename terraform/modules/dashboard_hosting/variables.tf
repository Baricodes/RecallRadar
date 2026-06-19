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
