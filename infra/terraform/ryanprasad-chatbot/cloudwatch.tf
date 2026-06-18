resource "aws_cloudwatch_log_group" "lambda_chat" {
  name              = "/aws/lambda/${var.name_prefix}-chat"
  retention_in_days = var.lambda_log_retention_days

  tags = merge(local.common_tags, {
    LogClass = "structured-app-events"
  })
}
