output "function_name" {
  description = "Name of the ingestion Lambda function."
  value       = aws_lambda_function.ingestion.function_name
}

output "function_arn" {
  description = "ARN of the ingestion Lambda function."
  value       = aws_lambda_function.ingestion.arn
}

output "role_arn" {
  description = "ARN of the ingestion Lambda IAM role."
  value       = aws_iam_role.ingestion.arn
}

output "role_name" {
  description = "Name of the ingestion Lambda IAM role."
  value       = aws_iam_role.ingestion.name
}

output "log_group_name" {
  description = "CloudWatch log group for the ingestion Lambda."
  value       = aws_cloudwatch_log_group.ingestion.name
}
