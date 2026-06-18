output "dynamodb_table_name" {
  description = "Name of the recalls DynamoDB table."
  value       = module.recalls_table.table_name
}

output "dynamodb_table_arn" {
  description = "ARN of the recalls DynamoDB table."
  value       = module.recalls_table.table_arn
}

output "ingestion_lambda_function_name" {
  description = "Name of the ingestion Lambda function."
  value       = module.ingestion_lambda.function_name
}

output "ingestion_lambda_function_arn" {
  description = "ARN of the ingestion Lambda function."
  value       = module.ingestion_lambda.function_arn
}

output "ingestion_lambda_role_arn" {
  description = "ARN of the IAM role used by the ingestion Lambda."
  value       = module.ingestion_lambda.role_arn
}

output "ingestion_lambda_invoke_command" {
  description = "AWS CLI command to manually invoke the ingestion Lambda."
  value       = "aws lambda invoke --function-name ${module.ingestion_lambda.function_name} --payload '{}' /tmp/recallradar-ingestion-response.json && cat /tmp/recallradar-ingestion-response.json"
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
  description = "Example curl commands to test the API."
  value = <<-EOT
    curl "${module.api_gateway.invoke_url}/recalls?limit=5"
    curl "${module.api_gateway.invoke_url}/recalls?classification=Class%20I&limit=5"
    curl "${module.api_gateway.invoke_url}/recalls?state=LA&limit=10"
    curl "${module.api_gateway.invoke_url}/recalls/stats"
  EOT
}
