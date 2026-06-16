# Security Preflight

Run these checks before deploying or running a lab/eval batch. Keep live outputs local or in lab S3; do not commit them.

## Bedrock model/profile checks

```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --by-provider Amazon \
  --by-output-modality TEXT

aws bedrock list-inference-profiles \
  --region us-east-1 \
  --type-equals SYSTEM_DEFINED

aws bedrock get-inference-profile \
  --region us-east-1 \
  --inference-profile-identifier us.amazon.nova-2-lite-v1:0

aws bedrock-runtime converse \
  --region us-east-1 \
  --model-id us.amazon.nova-2-lite-v1:0 \
  --messages '[{"role":"user","content":[{"text":"Reply with ok."}]}]' \
  --inference-config '{"maxTokens":16}' \
  --request-metadata '{"request_class":"preflight"}'
```

## IAM checks

- Runtime Lambda role should allow `bedrock:InvokeModel` only for selected model/profile resources.
- Add `bedrock:GetInferenceProfile` when using an inference profile.
- Do not attach `AmazonBedrockFullAccess` to the runtime Lambda role.
- Do not use `bedrock:*` in runtime policies.

## Invocation logging

Bedrock invocation logging is lab/eval capture only. Use S3 delivery, same Region/account, KMS-encrypted bucket defaults, and lifecycle expiration for raw logs. Raw model I/O stays out of git.
