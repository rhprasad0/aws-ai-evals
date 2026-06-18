# Week 3: Backend Instrumentation

Week 3 makes the chatbot observable enough to evaluate. The app should explain what happened at the Lambda/Bedrock boundary without dumping raw prompts, profile text, model responses, or provider traces into public-ish logs.

## Current app log contract

The backend emits structured CloudWatch application logs for safe app response events:

- `event`: `chat_response_completed`
- `response_source`: `bedrock` or `guardrail`
- `request_class`: `chat`
- `prompt_template_version`: current prompt contract version
- `model_id` and `max_tokens`
- `citation_labels` and `citation_count`
- `evidence_strength`
- `unsupported_claim_count`
- `elapsed_ms` for Bedrock-backed responses
- `input_tokens`, `output_tokens`, and `total_tokens` when Bedrock returns usage metadata

The backend also emits structured CloudWatch application logs for Bedrock boundary failures:

- `event`: `bedrock_converse_failure` or `bedrock_response_contract_failure`
- `boundary`: `lambda_to_bedrock`
- `operation`: `Converse`
- `model_id`: configured Bedrock model/profile ID
- `exception_type`: Python exception class name
- `elapsed_ms`: duration of the Bedrock call/response-parse path
- `aws_error_code`, `http_status_code`, `aws_request_id`, `retry_attempts` when AWS SDK metadata is available

These logs are for operational failure analysis. They intentionally exclude:

- user prompt text
- bundled public profile/source text
- raw model response text
- provider error messages
- stack traces that can contain response snippets
- private AWS account IDs, ARNs, or local paths

## CloudWatch wiring

Terraform owns the Lambda log group explicitly:

- log group: `/aws/lambda/<name-prefix>-chat`
- retention: `var.lambda_log_retention_days`, default `14`
- output: `lambda_log_group_name`

Sample CloudWatch Logs Insights queries live in `queries/aws-evals/cloudwatch-errors.txt`. Athena/S3 failure-slice queries for durable normalized JSONL artifacts live in `queries/aws-evals/failure-slices.sql`.

The normalized export contract for these events lives at `schemas/aws-evals/normalized-app-event.schema.json`. Export tooling should add `schema_version: normalized-app-event/v1` when converting CloudWatch app-event log lines into JSONL records.

Export recent CloudWatch app events to local normalized JSONL with:

```bash
python3 scripts/export_chat_app_events.py \
  --since-minutes 180 \
  --output /tmp/aws-evals/app-events/latest.jsonl

python3 scripts/validate_dataset.py \
  --schema schemas/aws-evals/normalized-app-event.schema.json \
  --input /tmp/aws-evals/app-events/latest.jsonl

python3 scripts/score_app_events.py \
  --input /tmp/aws-evals/app-events/latest.jsonl \
  --fail-on-score
```

For durable lab artifacts, pass `--s3-uri s3://<eval-artifacts-bucket>/app-events/normalized/<run_id>.jsonl` after confirming the local JSONL is public-safe, schema-valid, and deterministically scored.

## Bedrock invocation logs are separate

Bedrock model invocation logging is **S3-only** for lab/eval runs and remains disabled by default. Those logs can contain raw model I/O, so they are treated as sensitive eval artifacts, not app logs and not public report material.

## Week 3 instrumentation status

The core Week 3 instrumentation spine is now in place: safe app events in CloudWatch, explicit log-group retention, normalized JSONL export, schema validation, deterministic app-event scoring, and S3/Athena query templates for failure slicing.
