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
