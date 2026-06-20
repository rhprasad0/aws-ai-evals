locals {
  bedrock_eval_judge_inference_profile_arn = "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/${var.bedrock_eval_judge_model_id}"
  bedrock_eval_judge_foundation_model_arns = [
    for region in var.bedrock_eval_judge_foundation_model_regions :
    "arn:${data.aws_partition.current.partition}:bedrock:${region}::foundation-model/${var.bedrock_eval_judge_foundation_model_id}"
  ]
}

data "aws_iam_policy_document" "bedrock_eval_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "bedrock_eval" {
  statement {
    sid    = "InvokeJudgeModel"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:CreateModelInvocationJob",
      "bedrock:StopModelInvocationJob"
    ]
    resources = concat(
      [local.bedrock_eval_judge_inference_profile_arn],
      local.bedrock_eval_judge_foundation_model_arns
    )
  }

  statement {
    sid    = "ReadWriteEvalArtifacts"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:GetBucketLocation",
      "s3:AbortMultipartUpload",
      "s3:ListBucketMultipartUploads"
    ]
    resources = [
      aws_s3_bucket.eval_artifacts.arn,
      "${aws_s3_bucket.eval_artifacts.arn}/*"
    ]
  }

  statement {
    sid    = "UseEvalArtifactsKmsKey"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey"
    ]
    resources = [aws_kms_key.eval_artifacts.arn]
  }
}

resource "aws_iam_role" "bedrock_eval" {
  name               = "${var.name_prefix}-bedrock-eval"
  assume_role_policy = data.aws_iam_policy_document.bedrock_eval_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy" "bedrock_eval" {
  name   = "${var.name_prefix}-bedrock-eval"
  role   = aws_iam_role.bedrock_eval.id
  policy = data.aws_iam_policy_document.bedrock_eval.json
}
