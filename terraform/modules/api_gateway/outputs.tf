output "api_id" {
  description = "ID of the REST API."
  value       = aws_api_gateway_rest_api.api.id
}

output "execution_arn" {
  description = "Execution ARN of the REST API."
  value       = aws_api_gateway_rest_api.api.execution_arn
}

output "invoke_url" {
  description = "Base invoke URL for the deployed API stage."
  value       = aws_api_gateway_stage.api.invoke_url
}

output "stage_name" {
  description = "Deployed stage name."
  value       = aws_api_gateway_stage.api.stage_name
}
