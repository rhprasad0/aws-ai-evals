variable "aws_region" {
  description = "AWS Region for the chatbot stack."
  type        = string
  default     = "us-east-1"
}

variable "name_prefix" {
  description = "Public-safe resource name prefix."
  type        = string
  default     = "rp-chatbot"
}

variable "allowed_origins" {
  description = "Origins allowed to call the chatbot API."
  type        = list(string)
  default     = ["https://chat.ryans-lab.click", "https://ryanprasad.ai"]
}

variable "custom_domain_name" {
  description = "Optional lowercase custom domain for the CloudFront frontend, for example chatbot.example.com."
  type        = string
  default     = null
}

variable "route53_zone_name" {
  description = "Optional public Route 53 zone name that contains custom_domain_name."
  type        = string
  default     = null
}

variable "bedrock_model_id" {
  description = "Bedrock inference profile or model ID for the chatbot."
  type        = string
  default     = "us.amazon.nova-2-lite-v1:0"
}

variable "profile_source_max_chars" {
  description = "Maximum bundled profile source size for prompt stuffing."
  type        = number
  default     = 51200
}

variable "lambda_zip_path" {
  description = "Path to the packaged Lambda zip created by CI/build tooling."
  type        = string
  default     = "build/chatbot-api.zip"
}

variable "enable_bedrock_invocation_logging" {
  description = "Enable S3-only Bedrock invocation logging for lab/eval runs."
  type        = bool
  default     = false
}
