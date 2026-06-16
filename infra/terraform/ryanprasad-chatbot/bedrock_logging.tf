resource "aws_bedrock_model_invocation_logging_configuration" "lab" {
  count = var.enable_bedrock_invocation_logging ? 1 : 0

  logging_config {
    embedding_data_delivery_enabled = false
    image_data_delivery_enabled     = false
    text_data_delivery_enabled      = true
    video_data_delivery_enabled     = false

    s3_config {
      bucket_name = aws_s3_bucket.eval_artifacts.bucket
      key_prefix  = "bedrock-invocation-logs/"
    }
  }
}
