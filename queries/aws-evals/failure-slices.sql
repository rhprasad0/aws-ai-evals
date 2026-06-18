-- Athena failure-slice queries for normalized candidate-chatbot app events.
-- Input artifact: schema-valid JSONL exported by scripts/export_chat_app_events.py.
-- Replace the LOCATION placeholder with the durable S3 prefix used for normalized app events.
-- Example prefix shape: s3://<eval-artifacts-bucket>/app-events/normalized/

CREATE DATABASE IF NOT EXISTS aws_evals;

-- Optional external table definition for JSONL records.
-- Keep this in a lab/eval database, not a production analytics namespace.
CREATE EXTERNAL TABLE IF NOT EXISTS aws_evals.normalized_app_events (
  schema_version string,
  event string,
  response_source string,
  request_class string,
  prompt_template_version string,
  model_id string,
  max_tokens int,
  citation_labels array<string>,
  citation_count int,
  evidence_strength string,
  unsupported_claim_count int,
  elapsed_ms int,
  input_tokens int,
  output_tokens int,
  total_tokens int
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://<eval-artifacts-bucket>/app-events/normalized/';

-- 1) Overall health by source and evidence label.
SELECT
  response_source,
  evidence_strength,
  COUNT(*) AS events,
  SUM(CASE WHEN citation_count = 0 THEN 1 ELSE 0 END) AS zero_citation_events,
  SUM(CASE WHEN unsupported_claim_count > 0 THEN 1 ELSE 0 END) AS unsupported_claim_events,
  APPROX_PERCENTILE(elapsed_ms, 0.50) AS p50_latency_ms,
  APPROX_PERCENTILE(elapsed_ms, 0.95) AS p95_latency_ms,
  SUM(total_tokens) AS total_tokens
FROM aws_evals.normalized_app_events
WHERE schema_version = 'normalized-app-event/v1'
GROUP BY response_source, evidence_strength
ORDER BY events DESC;

-- 2) Deterministic failure slices matching scripts/score_app_events.py.
WITH scored AS (
  SELECT
    *,
    CASE
      WHEN evidence_strength IN ('unsupported', 'unsupported_private')
        AND (citation_count <> 0 OR CARDINALITY(citation_labels) <> 0)
        THEN 'unsupported_event_has_citations'
      WHEN evidence_strength IN ('unsupported', 'unsupported_private')
        AND unsupported_claim_count < 1
        THEN 'unsupported_event_missing_claim_count'
      WHEN evidence_strength IN ('high_public_project', 'medium_high_public_project', 'medium_high_lab_project', 'weak_support')
        AND citation_count = 0
        THEN 'supported_event_missing_citations'
      WHEN response_source = 'guardrail'
        AND (input_tokens IS NOT NULL OR output_tokens IS NOT NULL OR total_tokens IS NOT NULL)
        THEN 'guardrail_event_has_token_usage'
      WHEN response_source = 'bedrock'
        AND elapsed_ms > 5000
        THEN 'latency_budget_exceeded'
      WHEN response_source = 'bedrock'
        AND total_tokens > 4000
        THEN 'token_budget_exceeded'
      WHEN response_source = 'bedrock'
        AND input_tokens IS NOT NULL
        AND output_tokens IS NOT NULL
        AND total_tokens IS NOT NULL
        AND input_tokens + output_tokens <> total_tokens
        THEN 'token_total_mismatch'
      ELSE NULL
    END AS failure_reason
  FROM aws_evals.normalized_app_events
  WHERE schema_version = 'normalized-app-event/v1'
)
SELECT
  failure_reason,
  response_source,
  evidence_strength,
  COUNT(*) AS events,
  APPROX_PERCENTILE(elapsed_ms, 0.95) AS p95_latency_ms,
  MAX(total_tokens) AS max_total_tokens
FROM scored
WHERE failure_reason IS NOT NULL
GROUP BY failure_reason, response_source, evidence_strength
ORDER BY events DESC, failure_reason;

-- 3) Citation-label distribution for supported Bedrock answers.
SELECT
  label AS citation_label,
  COUNT(*) AS events
FROM aws_evals.normalized_app_events
CROSS JOIN UNNEST(citation_labels) AS t(label)
WHERE schema_version = 'normalized-app-event/v1'
  AND response_source = 'bedrock'
  AND evidence_strength NOT IN ('unsupported', 'unsupported_private')
GROUP BY label
ORDER BY events DESC, citation_label;

-- 4) Cost/latency watch for Bedrock-backed responses.
SELECT
  model_id,
  prompt_template_version,
  COUNT(*) AS bedrock_events,
  APPROX_PERCENTILE(elapsed_ms, 0.50) AS p50_latency_ms,
  APPROX_PERCENTILE(elapsed_ms, 0.95) AS p95_latency_ms,
  AVG(input_tokens) AS avg_input_tokens,
  AVG(output_tokens) AS avg_output_tokens,
  AVG(total_tokens) AS avg_total_tokens,
  SUM(total_tokens) AS total_tokens
FROM aws_evals.normalized_app_events
WHERE schema_version = 'normalized-app-event/v1'
  AND response_source = 'bedrock'
GROUP BY model_id, prompt_template_version
ORDER BY bedrock_events DESC;
