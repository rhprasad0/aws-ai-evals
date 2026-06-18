output "frontend_bucket_name" {
  description = "Private S3 bucket for frontend assets."
  value       = aws_s3_bucket.frontend.bucket
}

output "eval_artifacts_bucket_name" {
  description = "Private S3 bucket for lab/eval artifacts, including normalized app-event JSONL and Athena query results."
  value       = aws_s3_bucket.eval_artifacts.bucket
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain for preview smoke tests."
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "custom_domain_name" {
  description = "Custom domain alias when configured."
  value       = var.custom_domain_name
}

output "api_endpoint" {
  description = "HTTP API endpoint for POST /api/chat."
  value       = aws_apigatewayv2_api.chatbot.api_endpoint
}

output "rate_limit_table_name" {
  description = "DynamoDB table for TTL-backed rate-limit counters."
  value       = aws_dynamodb_table.rate_limits.name
}

output "lambda_log_group_name" {
  description = "CloudWatch log group for structured Lambda application logs."
  value       = aws_cloudwatch_log_group.lambda_chat.name
}
