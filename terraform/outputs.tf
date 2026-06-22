output "dynamodb_table_name" {
  description = "Name of the recalls DynamoDB table."
  value       = module.recalls_table.table_name
}

output "dynamodb_table_arn" {
  description = "ARN of the recalls DynamoDB table."
  value       = module.recalls_table.table_arn
}

output "ingestion_lambda_function_name" {
  description = "Names of the source-specific ingestion Lambda functions."
  value       = { for source, lambda in module.ingestion_lambda : source => lambda.function_name }
}

output "ingestion_lambda_function_arn" {
  description = "ARNs of the source-specific ingestion Lambda functions."
  value       = { for source, lambda in module.ingestion_lambda : source => lambda.function_arn }
}

output "ingestion_lambda_role_arn" {
  description = "ARNs of the IAM roles used by ingestion Lambdas."
  value       = { for source, lambda in module.ingestion_lambda : source => lambda.role_arn }
}

output "ingestion_lambda_invoke_command" {
  description = "AWS CLI command to manually invoke the Phase 3 ingestion state machine."
  value       = "aws stepfunctions start-execution --state-machine-arn ${aws_sfn_state_machine.recall_ingestion.arn} --input '{\"limit\":100}'"
}

output "ingestion_state_machine_arn" {
  description = "ARN of the Phase 3 multi-source ingestion state machine."
  value       = aws_sfn_state_machine.recall_ingestion.arn
}

output "ingestion_schedule_name" {
  description = "EventBridge Scheduler schedule name for ingestion."
  value       = module.ingestion_scheduler.schedule_name
}

output "ingestion_dlq_url" {
  description = "SQS dead-letter queue URL for failed schedule invocations."
  value       = module.ingestion_scheduler.dlq_url
}

output "query_lambda_function_name" {
  description = "Name of the query Lambda function."
  value       = module.query_lambda.function_name
}

output "query_lambda_function_arn" {
  description = "ARN of the query Lambda function."
  value       = module.query_lambda.function_arn
}

output "api_gateway_invoke_url" {
  description = "Base URL for the RecallRadar REST API."
  value       = module.api_gateway.invoke_url
}

output "api_test_commands" {
  description = "Example curl commands to test the API through CloudFront."
  value       = <<-EOT
    curl "${module.dashboard_hosting.cloudfront_url}/api/recalls?limit=5"
    curl "${module.dashboard_hosting.cloudfront_url}/api/recalls?source=FDA_DRUG&limit=5"
    curl "${module.dashboard_hosting.cloudfront_url}/api/recalls?category=VEHICLE&limit=5"
    curl "${module.dashboard_hosting.cloudfront_url}/api/recalls?classification=Class%20I&limit=5"
    curl "${module.dashboard_hosting.cloudfront_url}/api/recalls?state=LA&limit=10"
    curl "${module.dashboard_hosting.cloudfront_url}/api/recalls/stats"
  EOT
}

output "dashboard_bucket_name" {
  description = "S3 bucket for the React dashboard build artifacts."
  value       = module.dashboard_hosting.bucket_name
}

output "cloudfront_url" {
  description = "HTTPS URL for the RecallRadar dashboard."
  value       = module.dashboard_hosting.cloudfront_url
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (for cache invalidation)."
  value       = module.dashboard_hosting.cloudfront_distribution_id
}

output "dashboard_deploy_command" {
  description = "Build and deploy the React dashboard to S3 + invalidate CloudFront."
  value       = "REACT_APP_API_URL=/api npm run build --prefix ../dashboard && aws s3 sync ../dashboard/build/ s3://${module.dashboard_hosting.bucket_name}/ --delete && aws cloudfront create-invalidation --distribution-id ${module.dashboard_hosting.cloudfront_distribution_id} --paths '/*'"
}

output "cloudwatch_dashboard_name" {
  description = "CloudWatch operations dashboard name."
  value       = module.monitoring.dashboard_name
}

output "alarm_sns_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarms."
  value       = module.monitoring.sns_topic_arn
}
