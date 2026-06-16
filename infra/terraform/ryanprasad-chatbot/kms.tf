resource "aws_kms_key" "eval_artifacts" {
  description             = "KMS key for candidate chatbot lab/eval artifacts"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags                    = local.common_tags
}

resource "aws_s3_bucket" "eval_artifacts" {
  bucket_prefix = "${var.name_prefix}-eval-artifacts-"
  tags          = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "eval_artifacts" {
  bucket                  = aws_s3_bucket.eval_artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "eval_artifacts" {
  bucket = aws_s3_bucket.eval_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.eval_artifacts.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "eval_artifacts" {
  bucket = aws_s3_bucket.eval_artifacts.id

  rule {
    id     = "expire-raw-bedrock-invocation-logs"
    status = "Enabled"

    filter {
      prefix = "bedrock-invocation-logs/"
    }

    expiration {
      days = 30
    }
  }
}
