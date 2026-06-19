output "bucket_name" {
  description = "Name of the dashboard S3 bucket."
  value       = aws_s3_bucket.dashboard.id
}

output "bucket_arn" {
  description = "ARN of the dashboard S3 bucket."
  value       = aws_s3_bucket.dashboard.arn
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID."
  value       = aws_cloudfront_distribution.dashboard.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (dashboard URL)."
  value       = aws_cloudfront_distribution.dashboard.domain_name
}

output "cloudfront_url" {
  description = "HTTPS URL for the dashboard."
  value       = "https://${aws_cloudfront_distribution.dashboard.domain_name}"
}
