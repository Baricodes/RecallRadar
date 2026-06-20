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

output "domain_name" {
  description = "Regional API Gateway domain name."
  value       = "${aws_api_gateway_rest_api.api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com"
}

output "stage_name" {
  description = "Deployed stage name."
  value       = aws_api_gateway_stage.api.stage_name
}

output "cloudfront_api_key_value" {
  description = "API key value that CloudFront sends to API Gateway."
  value       = aws_api_gateway_api_key.cloudfront.value
  sensitive   = true
}
