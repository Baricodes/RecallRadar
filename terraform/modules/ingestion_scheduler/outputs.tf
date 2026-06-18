output "schedule_arn" {
  description = "ARN of the EventBridge Scheduler schedule."
  value       = aws_scheduler_schedule.ingestion.arn
}

output "schedule_name" {
  description = "Name of the EventBridge Scheduler schedule."
  value       = aws_scheduler_schedule.ingestion.name
}

output "dlq_arn" {
  description = "ARN of the dead-letter queue for failed schedule invocations."
  value       = aws_sqs_queue.dlq.arn
}

output "dlq_url" {
  description = "URL of the dead-letter queue."
  value       = aws_sqs_queue.dlq.url
}

output "scheduler_role_arn" {
  description = "ARN of the IAM role used by EventBridge Scheduler."
  value       = aws_iam_role.scheduler.arn
}
