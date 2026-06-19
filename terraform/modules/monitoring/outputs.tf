output "dashboard_name" {
  description = "CloudWatch operations dashboard name."
  value       = aws_cloudwatch_dashboard.operations.dashboard_name
}

output "sns_topic_arn" {
  description = "SNS topic ARN for alarm notifications."
  value       = aws_sns_topic.alarms.arn
}

output "alarm_names" {
  description = "Configured CloudWatch alarm names."
  value = [
    aws_cloudwatch_metric_alarm.ingestion_errors.alarm_name,
    aws_cloudwatch_metric_alarm.dlq_messages.alarm_name,
    aws_cloudwatch_metric_alarm.api_5xx.alarm_name,
  ]
}
