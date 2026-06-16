resource "aws_lambda_function" "chat" {
  function_name    = "${var.name_prefix}-chat"
  role             = aws_iam_role.lambda.arn
  handler          = "chatbot_api.handler.lambda_handler"
  runtime          = "python3.12"
  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  memory_size      = 512
  timeout          = 30

  environment {
    variables = {
      BEDROCK_MODEL_ID         = var.bedrock_model_id
      BEDROCK_MAX_TOKENS       = "768"
      PROFILE_SOURCE_MAX_CHARS = tostring(var.profile_source_max_chars)
      PROFILE_SOURCE_PATH      = "content/profile.md"
      RATE_LIMIT_TABLE_NAME    = aws_dynamodb_table.rate_limits.name
    }
  }

  tags = local.common_tags
}
