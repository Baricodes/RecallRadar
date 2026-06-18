output "function_name" {
  description = "Name of the query Lambda function."
  value       = aws_lambda_function.query.function_name
}

output "function_arn" {
  description = "ARN of the query Lambda function."
  value       = aws_lambda_function.query.arn
}

output "invoke_arn" {
  description = "Invoke ARN of the query Lambda (for API Gateway integration)."
  value       = aws_lambda_function.query.invoke_arn
}

output "role_arn" {
  description = "ARN of the query Lambda IAM role."
  value       = aws_iam_role.query.arn
}

output "role_name" {
  description = "Name of the query Lambda IAM role."
  value       = aws_iam_role.query.name
}

output "log_group_name" {
  description = "CloudWatch log group for the query Lambda."
  value       = aws_cloudwatch_log_group.query.name
}
