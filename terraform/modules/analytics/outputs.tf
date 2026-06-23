output "analytics_table_name" {
  description = "Name of the analytics DynamoDB table."
  value       = aws_dynamodb_table.analytics.name
}

output "analytics_table_arn" {
  description = "ARN of the analytics DynamoDB table."
  value       = aws_dynamodb_table.analytics.arn
}

output "stream_aggregator_function_name" {
  description = "Name of the stream aggregation Lambda."
  value       = aws_lambda_function.stream_aggregator.function_name
}

output "trend_compute_function_name" {
  description = "Name of the trend computation Lambda."
  value       = aws_lambda_function.trend_compute.function_name
}

output "briefing_generator_function_name" {
  description = "Name of the briefing generator Lambda."
  value       = aws_lambda_function.briefing_generator.function_name
}

output "briefing_bucket_name" {
  description = "S3 bucket storing archived weekly briefings."
  value       = aws_s3_bucket.briefings.bucket
}

output "state_machine_arn" {
  description = "ARN of the weekly analytics Step Functions state machine."
  value       = aws_sfn_state_machine.weekly_analytics.arn
}
