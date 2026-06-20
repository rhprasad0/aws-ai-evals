# Week 4 — Bedrock Model Evaluations Runbook

Week 4 proves the managed Bedrock model-evaluation lane without building a custom judge platform too early.

The target path is:

```text
captured chatbot responses
→ Bedrock model-eval BYOI JSONL
→ S3 input object
→ Bedrock create-evaluation-job
→ S3 managed output/report artifacts
→ compare judge results against deterministic scorer notes
```

## Boundary for this week

Use **BYOI** (`precomputedInferenceSource`) so Bedrock judges the app's captured response, not a raw model invoked outside the chatbot boundary.

This runbook does not commit real AWS identifiers. Replace placeholders only in a local scratch copy, never in the tracked template.

Keep out of the repo:

- real AWS account IDs, ARNs, bucket names, and job IDs;
- raw provider responses and Bedrock invocation logs;
- unredacted S3 result folders;
- local scratch JSONL files from live captures.

Commit only public-safe adapter code, placeholder templates, runbook notes, and sanitized receipts.

## 1. Local preflight

Run the local validation lane first. Bedrock should only see rows that already passed schema and public-safety checks.

```bash
python3 -m unittest tests.test_bedrock_model_eval_adapter tests.test_bedrock_eval_job_template -v
python3 -m json.tool infra/templates/bedrock-model-eval-job.json >/tmp/bedrock-model-eval-job.formatted.json
python3 scripts/public_safety_scan.py src scripts tests schemas datasets/synthetic infra/templates docs/week-04-model-evals-runbook.md
git diff --check
```

If the capture source is live chatbot output, capture and score it first:

```bash
RUN_ID="week4-model-eval-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "/tmp/${RUN_ID}"

python3 scripts/capture_candidate_chatbot_responses.py \
  --endpoint https://chat.ryans-lab.click/api/chat \
  --output "/tmp/${RUN_ID}/live-capture.jsonl" \
  --ids recruiter_container_orchestration,unsupported_large_k8s_prod,private_sources_refusal \
  --fail-on-request \
  --fail-on-score
```

For a full batch, omit `--ids` after the smoke path is clean.

## 2. Build the BYOI JSONL

Convert captured app responses into Bedrock model-as-judge BYOI rows:

```bash
MODEL_IDENTIFIER="ryanprasad-ai-chatbot-v1-week4-local"

python3 scripts/bedrock_byoi_adapter.py \
  --dataset datasets/synthetic/recruiter-evidence-qa.jsonl \
  --input "/tmp/${RUN_ID}/live-capture.jsonl" \
  --output "/tmp/${RUN_ID}/bedrock-model-eval-byoi.jsonl" \
  --model-identifier "${MODEL_IDENTIFIER}"

python3 scripts/validate_dataset.py \
  --schema schemas/bedrock-model-eval-byoi.schema.json \
  --input "/tmp/${RUN_ID}/bedrock-model-eval-byoi.jsonl"
```

Adapter invariants:

- one `modelResponses[]` entry per prompt;
- one `modelResponses[].modelIdentifier` value per job;
- `prompt`, `referenceResponse`, `category`, and `modelResponses[].response` are populated;
- duplicate captured answer IDs fail locally;
- `responseValid=false` rows fail locally by default;
- deterministic score failures may still be exported when the response contract is valid, because they are useful judge-calibration examples.

## 3. Prepare AWS preflight values

Use a sandbox account/region. Before submission, confirm:

- the evaluator model is available in the selected region;
- model access is enabled for the evaluator model;
- the Terraform-managed Bedrock evaluation service role can read the input S3 object and write to the output prefix;
- the S3 bucket has the intended encryption and retention posture;
- quotas and dataset size are bounded enough for a cheap Week 4 run;
- the `MODEL_IDENTIFIER` value exactly matches `inferenceConfig.models[0].precomputedInferenceSource.inferenceSourceIdentifier`.

The reusable IAM runway lives in Terraform. Plan/apply it with the same domain variables used for the chatbot stack so Terraform does not interpret omitted optional domain variables as a request to remove the custom domain:

```bash
terraform -chdir=infra/terraform/ryanprasad-chatbot validate
terraform -chdir=infra/terraform/ryanprasad-chatbot plan \
  -var='custom_domain_name=chat.ryans-lab.click' \
  -var='route53_zone_name=ryans-lab.click'
```

After apply, read the service role ARN from Terraform output into local scratch state:

```bash
BEDROCK_EVAL_ROLE_ARN="$(terraform -chdir=infra/terraform/ryanprasad-chatbot output -raw bedrock_eval_role_arn)"
```

Suggested scratch variables:

```bash
AWS_REGION="us-east-1"
INPUT_S3_URI="s3://<EVAL_BUCKET>/input/${RUN_ID}/bedrock-model-eval-byoi.jsonl"
OUTPUT_S3_URI="s3://<EVAL_BUCKET>/output/model-evals/${RUN_ID}/"
EVALUATOR_MODEL_ID="<EVALUATOR_MODEL_ID>"
JOB_NAME="candidate-byoi-<lowercase-sanitized-run-id>"
```

Do not paste real values into tracked files.

Bedrock evaluation job names must match `[a-z0-9](-*[a-z0-9]){0,62}`. Sanitize timestamps before rendering the request; uppercase `T`/`Z` timestamp characters will fail validation.

Some evaluator models, including Nova-family models in regions where on-demand direct invocation is not supported, require an inference profile ID/ARN such as a regional/system profile. If Bedrock rejects direct model invocation, retry with the supported inference profile and make sure the service role can invoke both the profile and its routed foundation-model ARNs.

## 4. Upload the BYOI dataset

Use an account-local bucket, not the placeholder `example-eval-bucket` from the tracked template.

```bash
aws s3 cp "/tmp/${RUN_ID}/bedrock-model-eval-byoi.jsonl" "${INPUT_S3_URI}" \
  --region "${AWS_REGION}"

aws s3 ls "${INPUT_S3_URI}" --region "${AWS_REGION}"
```

If upload fails, record the blocker as one of:

- S3 bucket/prefix missing;
- IAM write denied;
- encryption/KMS denied;
- region mismatch;
- local file missing or invalid.

## 5. Render a local job request

Copy `infra/templates/bedrock-model-eval-job.json` to `/tmp` and replace placeholders there.

```bash
JOB_REQUEST="/tmp/${RUN_ID}/bedrock-model-eval-job.json"
cp infra/templates/bedrock-model-eval-job.json "${JOB_REQUEST}"

python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["JOB_REQUEST"])
text = path.read_text(encoding="utf-8")
replacements = {
    "<BEDROCK_EVAL_JOB_NAME>": os.environ["JOB_NAME"],
    "<BEDROCK_EVAL_ROLE_ARN>": os.environ["BEDROCK_EVAL_ROLE_ARN"],
    "s3://example-eval-bucket/input/bedrock-model-eval-byoi.jsonl": os.environ["INPUT_S3_URI"],
    "s3://example-eval-bucket/output/model-evals/": os.environ["OUTPUT_S3_URI"],
    "<EVALUATOR_MODEL_ID>": os.environ["EVALUATOR_MODEL_ID"],
    "<BYOI_MODEL_IDENTIFIER>": os.environ["MODEL_IDENTIFIER"],
}
for old, new in replacements.items():
    text = text.replace(old, new)
json.loads(text)
path.write_text(text, encoding="utf-8")
print(path)
PY

python3 -m json.tool "${JOB_REQUEST}" >/tmp/bedrock-model-eval-job.rendered.json
```

Check the rendered request manually before submitting. The tracked template is intentionally boring; the scratch copy is where real values live.

## 6. Submit the Bedrock evaluation job

Submit with the Bedrock control-plane API:

```bash
aws bedrock create-evaluation-job \
  --cli-input-json "file://${JOB_REQUEST}" \
  --region "${AWS_REGION}" \
  >/tmp/${RUN_ID}/create-evaluation-job-response.json

python3 -m json.tool "/tmp/${RUN_ID}/create-evaluation-job-response.json"
```

Expected useful fields include the job ARN/name/status fields returned by the API. Keep the raw response in `/tmp` or private notes; do not commit it if it contains account identifiers.

If submission fails, classify the blocker:

- **schema** — Bedrock rejects the BYOI shape or request payload;
- **IAM** — service role cannot access S3, KMS, or Bedrock;
- **model access** — evaluator model unavailable or not enabled;
- **region** — feature/metric/model not available in the selected region;
- **quota/cost** — token throughput, concurrent job, prompt-count, or cost guardrail issue;
- **S3** — input object unreadable or output prefix unwritable.

A precise blocker is an acceptable Week 4 receipt. “AWS said no” is not precise enough; make the wall inspectable.

## 7. Inspect job status

Use the job identifier from the create response.

```bash
JOB_IDENTIFIER="<JOB_IDENTIFIER_FROM_CREATE_RESPONSE>"

aws bedrock get-evaluation-job \
  --job-identifier "${JOB_IDENTIFIER}" \
  --region "${AWS_REGION}" \
  >/tmp/${RUN_ID}/get-evaluation-job-response.json

python3 -m json.tool "/tmp/${RUN_ID}/get-evaluation-job-response.json"
```

Poll until the job reaches a terminal state. Record:

- status;
- failure reason, if any;
- evaluator model;
- metric names;
- input S3 URI;
- output S3 URI;
- rough prompt count and run size;
- whether BYOI skipped candidate model invocation as expected.

## 8. Inspect S3 output artifacts

List the managed output prefix:

```bash
aws s3 ls "${OUTPUT_S3_URI}" --recursive --region "${AWS_REGION}"
```

Download only to local scratch/private storage:

```bash
mkdir -p "/tmp/${RUN_ID}/bedrock-output"
aws s3 cp "${OUTPUT_S3_URI}" "/tmp/${RUN_ID}/bedrock-output/" \
  --recursive \
  --region "${AWS_REGION}"
```

Before promoting any excerpt into docs, check it for:

- account IDs or ARNs;
- real bucket names;
- raw prompts/answers that should stay private;
- provider responses;
- local paths;
- emails, Slack IDs, private hostnames, or IPs.

## 9. Compare managed judge output to deterministic gates

The deterministic scorer remains the hard-boundary source of truth. Bedrock judge output is useful for fuzzier quality questions.

Record any mismatch like this:

```text
Dataset row: <row_id>
Deterministic scorer: pass|fail, reason=<citation|overclaim|private-source|refusal|schema>
Bedrock judge metric: <metric_name>, score/result=<public-safe summary>
Interpretation: judge agreed|judge missed hard boundary|judge flagged quality issue scorer does not cover
Next action: no-op|rubric note|dataset fix|app guardrail|human review
```

Do not turn one Bedrock score into a regression gate in Week 4. Week 5 is where repeated-run variance and judge-vs-human calibration decide whether a judge metric is stable enough to gate anything.

## 10. Week 4 receipt format

Create a short private note or sanitized doc snippet with one of these outcomes.

Successful run receipt:

```text
Week 4 Bedrock model eval receipt
Run ID: <RUN_ID>
Dataset: bedrock-model-eval-byoi/v1, rows=<N>
BYOI model identifier: <PUBLIC_SAFE_LABEL>
Evaluator model: <MODEL_FAMILY_OR_PLACEHOLDER>
Metrics: Builtin.Correctness, Builtin.Completeness
Job status: completed
Output shape observed: <brief public-safe summary of files/report folders>
Deterministic-vs-managed note: <one or two scoped observations>
Cost/token note: <rough non-sensitive estimate or "not captured">
```

Blocked run receipt:

```text
Week 4 Bedrock model eval blocker
Run ID: <RUN_ID>
Dataset: bedrock-model-eval-byoi/v1, rows=<N>
Blocked at: preflight|upload|create-evaluation-job|get-evaluation-job|output-inspection
Blocker class: IAM|model-access|region|quota-cost|S3|schema|unknown
Public-safe summary: <what failed without account IDs/ARNs/buckets>
Next check: <smallest concrete action>
```

## 11. Cleanup

For scratch files:

```bash
rm -rf "/tmp/${RUN_ID}"
```

For AWS artifacts, follow the sandbox retention policy. If deleting the test objects is appropriate:

```bash
aws s3 rm "${INPUT_S3_URI}" --region "${AWS_REGION}"
aws s3 rm "${OUTPUT_S3_URI}" --recursive --region "${AWS_REGION}"
```

Do not delete artifacts that are needed for private evidence until the receipt/blocker note is written.

## Final local verification before commit

```bash
python3 -m unittest discover -v
python3 scripts/public_safety_scan.py src scripts tests schemas datasets/synthetic infra/templates docs/week-04-model-evals-runbook.md
git diff --check
```

The bouncer still checks IDs. The Bedrock judge just gets a clipboard.
