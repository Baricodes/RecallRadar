output "table_name" {
  description = "Name of the DynamoDB table."
  value       = aws_dynamodb_table.recalls.name
}

output "table_arn" {
  description = "ARN of the DynamoDB table."
  value       = aws_dynamodb_table.recalls.arn
}

output "table_id" {
  description = "ID of the DynamoDB table."
  value       = aws_dynamodb_table.recalls.id
}

output "stream_arn" {
  description = "ARN of the DynamoDB stream for recall inserts."
  value       = aws_dynamodb_table.recalls.stream_arn
}
