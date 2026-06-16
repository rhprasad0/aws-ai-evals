locals {
  bedrock_inference_profile_arn = "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/${var.bedrock_model_id}"
  bedrock_inference_resources = [
    "arn:${data.aws_partition.current.partition}:bedrock:us-east-1::foundation-model/amazon.nova-2-lite-v1:0",
    "arn:${data.aws_partition.current.partition}:bedrock:us-east-2::foundation-model/amazon.nova-2-lite-v1:0",
    "arn:${data.aws_partition.current.partition}:bedrock:us-west-2::foundation-model/amazon.nova-2-lite-v1:0",
    local.bedrock_inference_profile_arn,
  ]
}

resource "aws_iam_role" "lambda" {
  name = "${var.name_prefix}-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "lambda_logs" {
  name = "${var.name_prefix}-lambda-logs"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.name_prefix}-chat:*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_bedrock" {
  name = "${var.name_prefix}-bedrock-runtime"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = local.bedrock_inference_resources
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:GetInferenceProfile"
        ]
        Resource = [local.bedrock_inference_profile_arn]
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_rate_limits" {
  name = "${var.name_prefix}-rate-limits"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.rate_limits.arn
      }
    ]
  })
}
