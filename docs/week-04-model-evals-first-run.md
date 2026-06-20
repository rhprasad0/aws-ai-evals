# Week 4 Bedrock Model Eval First Run

Date: 2026-06-20

## Outcome

The first Bedrock model-evaluation BYOI run completed successfully in the sandbox AWS account.

This was a managed Bedrock model-as-judge job over captured chatbot responses. Bedrock used `precomputedInferenceSource`, so it judged the supplied app responses instead of invoking the candidate chatbot/model itself.

## Local input

- Dataset schema: `bedrock-model-eval-byoi/v1`
- BYOI rows: 21
- Captured responses: 21 valid chatbot responses
- Deterministic scorer: 20 passed, 1 failed
- Deterministic failure:
  - `recruiter_cloud_security_boundaries` — missing required phrase: `secrets`

The deterministic failure was intentionally still useful for BYOI judge calibration because the response contract was valid.

## Managed Bedrock job shape

- Evaluation type: model-as-judge with built-in metrics
- Inference source: BYOI / precomputed inference
- Evaluator model path: Nova 2 Lite via a cross-region inference profile
- Metrics:
  - `Builtin.Correctness`
  - `Builtin.Completeness`
- Output destination: private sandbox S3 eval-artifacts prefix

Tracked repo files still use placeholders only. Real S3 URIs, role ARNs, account IDs, and job identifiers were kept in `/tmp` and AWS, not committed.

## Output shape observed

Bedrock wrote two artifacts under the managed output prefix:

```text
<job-name>/amazon-bedrock-evaluations-permission-check
<job-name>/<job-id>/models/<byoi-model-identifier>/taskTypes/General/datasets/candidate_evidence_chatbot_byoi/<uuid>_output.jsonl
```

The output JSONL had 21 rows. Each row used this top-level shape:

```text
automatedEvaluationResult
inputRecord
modelResponses
```

The `automatedEvaluationResult.scores[]` entries used:

```text
metricName
result
evaluatorDetails
```

## Score distribution

```text
Builtin.Correctness
- 1.0: 20 rows
- 0.5: 1 row

Builtin.Completeness
- 1.0: 14 rows
- 0.75: 6 rows
- 0.25: 1 row
```

For the deterministic failure row:

```text
row_id: recruiter_cloud_security_boundaries
deterministic scorer: failed, missing required phrase `secrets`
Bedrock Correctness: 0.5
Bedrock Completeness: 0.25
```

That is the right kind of Week 4 learning artifact: the deterministic scorer caught a hard expected-content miss, and the managed judge also downgraded the answer on fuzzy quality metrics.

## First-run blockers encountered

1. **Job name validation**
   - Bedrock requires job names matching `[a-z0-9](-*[a-z0-9]){0,62}`.
   - The first rendered job name used timestamp characters that violated the pattern.
   - Fix: lowercase/sanitize the run ID before rendering `jobName`.

2. **Evaluator model invocation path**
   - Direct `amazon.nova-2-lite-v1:0` on-demand invocation was rejected for the evaluation job.
   - Bedrock required an inference profile ID/ARN for that model.
   - Fix: use the regional/system inference profile for Nova 2 Lite and grant the service role both inference-profile and routed foundation-model permissions.

## Follow-up infrastructure cleanup

After the first run, the reusable Bedrock model-eval IAM runway was moved into Terraform:

- `aws_iam_role.bedrock_eval`
- `aws_iam_role_policy.bedrock_eval`
- `output.bedrock_eval_role_arn`

The Terraform-managed role is the repeat-run path for Week 5 calibration. Per-run job request JSON, BYOI JSONL, job IDs, and raw Bedrock output stay as scratch/private artifacts.

When planning this stack, pass the same custom-domain variables used for the deployed chatbot; omitting them can make Terraform plan unrelated domain/certificate removals.

## Interpretation

Week 4's managed path is now real:

```text
live chatbot capture
→ deterministic scoring
→ BYOI JSONL
→ S3 input
→ Bedrock create-evaluation-job
→ completed managed output JSONL
→ deterministic-vs-managed comparison
```

Do not promote the Bedrock scores to regression gates yet. Week 5 still needs repeated-run variance and judge-vs-human calibration.
