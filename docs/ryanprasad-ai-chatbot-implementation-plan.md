# ryanprasad.ai Candidate Evidence Chatbot V1 Implementation Plan

## Goal

Build the V1 `ryanprasad.ai` recruiter-facing skills evidence chatbot and its first eval gates. V1 answers recruiter-style questions from `content/profile.md`, returns citations/source labels, calibrates evidence strength, refuses unsupported or private-source requests, and records lab/eval evidence without committing raw provider output.

This is an implementation plan, not implementation code. It intentionally excludes Calendar, Slack, RAG, vector databases, login, durable transcript storage, and an admin dashboard.

## Source Inputs

Read before implementation:

- `AGENTS.md`
- `README.md`
- `docs/ryanprasad-ai-chatbot.md`
- `docs/aws-ai-evals-learning-plan.md`
- `content/profile.md`
- `datasets/synthetic/recruiter-evidence-qa.jsonl`

AWS docs to re-check during implementation because service schemas and limits change:

- Bedrock Converse API: <https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html>
- Nova 2 Lite model card: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-2-lite.html>
- `ListFoundationModels`: <https://docs.aws.amazon.com/bedrock/latest/APIReference/API_ListFoundationModels.html>
- `ListInferenceProfiles`: <https://docs.aws.amazon.com/bedrock/latest/APIReference/API_ListInferenceProfiles.html>
- `GetInferenceProfile`: <https://docs.aws.amazon.com/bedrock/latest/APIReference/API_GetInferenceProfile.html>
- Bedrock model access: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html>
- Bedrock quotas: <https://docs.aws.amazon.com/bedrock/latest/userguide/quotas.html>
- Bedrock model invocation logging: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html>
- Bedrock model-as-judge prompt/BYOI datasets: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-prompt-datasets-judge.html>

## V1 Scope

V1 includes:

- React + Vite + TypeScript single-page chatbot.
- CloudFront distribution in front of a private S3 SPA bucket.
- API Gateway HTTP API route `POST /api/chat`.
- Python Lambda chat backend.
- DynamoDB TTL table for salted hashed IP/session rate-limit counters.
- Prompt-stuffed `content/profile.md` as the canonical source.
- Stable citations/source labels, not chunk-level RAG citations.
- Evidence-strength labels.
- Bedrock Runtime Converse API with default model/profile `us.amazon.nova-2-lite-v1:0`.
- Explicit `maxTokens: 768` for visitor-facing chatbot calls.
- Bedrock preflight for model/profile availability, access, quota, IAM scope, and a Converse smoke test.
- S3-only Bedrock invocation logging for lab/eval runs, with KMS encryption and lifecycle expiration.
- Local deterministic eval gates for schema, citation support, overclaiming, refusal behavior, and public safety.
- Bedrock BYOI regression batches from captured chatbot outputs.
- 3x judge calibration and human-label review before any judge metric becomes a release gate.

V1 excludes:

- Calendar booking, Slack relay, email automation, proactive outreach, or write tools.
- RAG, vector DBs, crawlers, search indexes, Bedrock Knowledge Bases, or README ingestion at runtime.
- Login, visitor accounts, admin dashboards, private memory, private notes, private repos, and durable visitor transcript storage.
- Committed raw model I/O, generated provider responses, raw invocation logs, raw traces, real AWS account details, real ARNs, real bucket names, local paths, private hostnames, private IPs, private emails, Slack IDs, calendar IDs, or secrets.

## Architecture

```text
Visitor browser
  -> CloudFront distribution with security headers
     -> private S3 SPA origin
     -> API Gateway HTTP API /api/chat
        -> Python Lambda chat backend
           -> source loader/sanitizer for bundled content/profile.md
           -> DynamoDB TTL rate-limit counters
           -> Bedrock Runtime Converse API
           -> app-level structured trace metadata

Lab/eval mode
  -> Bedrock invocation logging
     -> same-Region encrypted S3 lab prefixes only
     -> normalized BYOI/regression artifacts under eval run prefixes
```

Core invariant: the browser never receives AWS internals, source file paths, secret names, account identifiers, or raw trace/log data. The backend owns system instructions, source loading, rate limits, Bedrock invocation, citation validation, and response shaping.

## Runtime Contracts

### API

Create `POST /api/chat`:

```json
{
  "sessionId": "opaque-session-id",
  "messages": [
    { "role": "user", "content": "Where does Ryan show container orchestration?" }
  ]
}
```

Return:

```json
{
  "answer": "Concise grounded answer.",
  "citations": ["aws-devops-lab README", "airgap-aiops README"],
  "evidenceStrength": "medium_high_lab_project",
  "unsupportedClaims": []
}
```

Rules:

- Accept only `user` and `assistant` roles from the client.
- Rebuild system/developer instructions server-side.
- Cap message count, per-message characters, and total payload size.
- Client max message length: 2,000 characters. Backend remains authoritative.
- No streaming in V1 unless explicitly chosen later.
- No transcript persistence in the application database.
- Generic user-facing errors for Bedrock timeout, unavailable model, quota, source-budget failure, and validation failure.

### Evidence Labels

Use stable labels from `content/profile.md` and the synthetic dataset. Initial allowlist:

- `content/profile.md`
- `GitHub Profile README`
- `aws-devops-lab README`
- `airgap-aiops README`
- `agent2agent-guestbook README`
- `closed-loop-ai-podcast README`
- `aws-ai-evals README`
- `ai-tamperguard README`
- `policy-bonfire-2 README`

Initial evidence-strength enum:

- `high_public_project`
- `medium_high_public_project`
- `medium_high_lab_project`
- `calibration_required`
- `weak_support`
- `unsupported`
- `unsupported_private`

Do not upgrade lab/public-project evidence into production-customer evidence unless `content/profile.md` explicitly supports that claim.

## Source Hardening

Implement source loading as a fail-closed subsystem.

Requirements:

- Bundle or load `content/profile.md` server-side only.
- Enforce `PROFILE_SOURCE_MAX_CHARS=51200` by default.
- Keep source load plus sanitization under a 3 second target at Lambda cold start.
- Remove or escape instruction-like role markers and control-token patterns before prompt assembly, including `System:`, `Developer:`, `Human:`, `Assistant:`, `User:`, `Tool:`, `[INST]`, `[/INST]`, `<s>`, `</s>`, and `<|...|>`-style control tokens.
- Preserve facts and source labels; do not silently truncate the canonical source.
- Fail closed if the source exceeds the configured budget or cannot be sanitized.
- Insert source content behind explicit delimiters:

```text
PUBLIC FACTS START
<sanitized profile.md contents>
PUBLIC FACTS END
```

Trap: stripping suspicious text is not the security boundary. The boundary is that source docs are facts, never runtime instructions.

## AWS Design

### Frontend Hosting

- S3 bucket is private.
- CloudFront uses the private S3 origin, preferably with Origin Access Control unless implementation-time AWS/Terraform docs require a different current pattern.
- SPA routes fall back to `index.html`.
- Security headers include HSTS, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and a restrictive CSP.
- CORS allows only `https://ryanprasad.ai` and explicitly approved preview origins.

### Backend

- Python Lambda, 512 MB memory, 30 second timeout.
- Short visitor-facing Bedrock timeout with a generic fallback response.
- Longer timeout allowed only for offline batch/eval scripts.
- API Gateway HTTP API route throttles start at 10 requests/second steady and 20 burst, then tune from observed traffic.
- DynamoDB table stores only counters, timestamps, route names, and coarse decisions.
- Rate-limit keys use salted hashes of IP/session plus time-window sort keys. Do not store raw IP addresses.
- TTL windows include short windows such as 5 minutes, hourly, and 24 hours.

### Bedrock Runtime

- Default model/profile: `us.amazon.nova-2-lite-v1:0`.
- Use `amazon.nova-2-lite-v1:0` only if preflight proves direct in-Region invocation works for the selected Region.
- Use `global.amazon.nova-2-lite-v1:0` only when the global routing tradeoff is explicit in the run manifest.
- Fail closed if Nova 2 Lite is unavailable unless an explicit lab fallback model is configured and recorded.
- Use Bedrock Runtime Converse API.
- Set `inferenceConfig.maxTokens` to `768` for visitor-facing calls.
- Include `requestMetadata` with a public-safe `run_id`/`request_class` for lab/eval correlation when supported. Do not include raw user text or private identifiers in metadata.

### Bedrock Preflight

Run before deploy and before any lab regression batch:

```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --by-provider Amazon \
  --by-output-modality TEXT
```

```bash
aws bedrock list-inference-profiles \
  --region us-east-1 \
  --type-equals SYSTEM_DEFINED
```

```bash
aws bedrock get-inference-profile \
  --region us-east-1 \
  --inference-profile-identifier us.amazon.nova-2-lite-v1:0
```

```bash
aws bedrock-runtime converse \
  --region us-east-1 \
  --model-id us.amazon.nova-2-lite-v1:0 \
  --messages '[{"role":"user","content":[{"text":"Reply with ok."}]}]' \
  --inference-config '{"maxTokens":16}' \
  --request-metadata '{"request_class":"preflight"}'
```

Also verify:

- Model access is enabled for the selected generator and evaluator models.
- Service Quotas cover public traffic and lab/eval batches.
- Runtime Lambda IAM allows only `bedrock:InvokeModel` on the selected foundation-model or inference-profile resources where AWS supports scoping.
- Add `bedrock:GetInferenceProfile` scoped to the selected profile when using an inference profile.
- Add `bedrock:InvokeModelWithResponseStream` only if streaming is implemented later.
- Preflight tooling may need `bedrock:ListFoundationModels`, `bedrock:ListInferenceProfiles`, and `bedrock:GetInferenceProfile`.
- Do not use `bedrock:*`, `Resource: "*"`, or `AmazonBedrockFullAccess` for the runtime Lambda role.

Doc verification needed before coding IAM: confirm the exact ARN forms and resource-level permission behavior for the selected model/profile in the current AWS docs and with `GetInferenceProfile`.

### Lab Invocation Logging

Use Bedrock model invocation logging for lab/eval runs only:

- S3 delivery only for raw model I/O.
- Same AWS account and same Region as the Bedrock logging configuration.
- KMS encryption on the destination bucket.
- Lifecycle expiration on raw log prefixes; default lab retention target is 30 days unless a run manifest overrides it.
- Text delivery enabled for V1. Image, embedding, video, and audio delivery disabled.
- Correlate logs to app traces by run ID or public-safe request metadata.
- Keep raw invocation logs out of CloudWatch and out of this repo.

Placeholder layout:

```text
s3://example-eval-bucket/bedrock-invocation-logs/
s3://example-eval-bucket/eval-runs/<run_id>/raw/
s3://example-eval-bucket/eval-runs/<run_id>/normalized/
s3://example-eval-bucket/eval-runs/<run_id>/reports/
```

## Exact Files To Create Or Modify

Create:

- `apps/ryanprasad-chatbot/frontend/package.json`
- `apps/ryanprasad-chatbot/frontend/vite.config.ts`
- `apps/ryanprasad-chatbot/frontend/tsconfig.json`
- `apps/ryanprasad-chatbot/frontend/src/main.tsx`
- `apps/ryanprasad-chatbot/frontend/src/App.tsx`
- `apps/ryanprasad-chatbot/frontend/src/api/chat.ts`
- `apps/ryanprasad-chatbot/frontend/src/components/ChatPanel.tsx`
- `apps/ryanprasad-chatbot/frontend/src/styles.css`
- `apps/ryanprasad-chatbot/backend/pyproject.toml`
- `apps/ryanprasad-chatbot/backend/src/chatbot_api/__init__.py`
- `apps/ryanprasad-chatbot/backend/src/chatbot_api/handler.py`
- `apps/ryanprasad-chatbot/backend/src/chatbot_api/settings.py`
- `apps/ryanprasad-chatbot/backend/src/chatbot_api/sources.py`
- `apps/ryanprasad-chatbot/backend/src/chatbot_api/prompting.py`
- `apps/ryanprasad-chatbot/backend/src/chatbot_api/bedrock.py`
- `apps/ryanprasad-chatbot/backend/src/chatbot_api/rate_limit.py`
- `apps/ryanprasad-chatbot/backend/src/chatbot_api/response_contract.py`
- `apps/ryanprasad-chatbot/backend/tests/test_sources.py`
- `apps/ryanprasad-chatbot/backend/tests/test_prompting.py`
- `apps/ryanprasad-chatbot/backend/tests/test_response_contract.py`
- `apps/ryanprasad-chatbot/backend/tests/test_rate_limit.py`
- `schemas/recruiter-evidence-qa.schema.json`
- `schemas/chat-response.schema.json`
- `schemas/bedrock-model-eval-byoi.schema.json`
- `schemas/run-manifest.schema.json`
- `schemas/examples/run-manifest.example.json`
- `scripts/validate_recruiter_evidence_dataset.py`
- `scripts/run_candidate_chatbot_eval.py`
- `scripts/bedrock_byoi_adapter.py`
- `scripts/bedrock_preflight.py`
- `scripts/public_safety_scan.py`
- `infra/terraform/ryanprasad-chatbot/main.tf`
- `infra/terraform/ryanprasad-chatbot/variables.tf`
- `infra/terraform/ryanprasad-chatbot/outputs.tf`
- `infra/terraform/ryanprasad-chatbot/s3_cloudfront.tf`
- `infra/terraform/ryanprasad-chatbot/api_gateway.tf`
- `infra/terraform/ryanprasad-chatbot/lambda.tf`
- `infra/terraform/ryanprasad-chatbot/iam.tf`
- `infra/terraform/ryanprasad-chatbot/dynamodb_rate_limits.tf`
- `infra/terraform/ryanprasad-chatbot/kms.tf`
- `infra/terraform/ryanprasad-chatbot/bedrock_logging.tf`
- `docs/ryanprasad-ai-chatbot-runbook.md`
- `docs/security-preflight.md`
- `docs/eval-gates.md`

Modify only if needed:

- `content/profile.md` to tighten public-safe evidence or source labels.
- `datasets/synthetic/recruiter-evidence-qa.jsonl` to add V1 cases, keeping every row synthetic/public-safe.
- `README.md` to link the implemented chatbot/runbook after the implementation exists.

Do not create V1 files for Calendar, Slack, RAG indexes, vector databases, login, admin UI, or private memory integrations.

## Ordered Phases

### Phase 0 - Contracts And Tooling

1. Add JSON schemas for `datasets/synthetic/recruiter-evidence-qa.jsonl`, chat responses, BYOI model-eval rows, and run manifests.
2. Build `scripts/validate_recruiter_evidence_dataset.py` to validate JSONL line-by-line and report line numbers.
3. Build `scripts/public_safety_scan.py` to block obvious secrets, account IDs, raw ARNs, private hostnames, private paths, real emails, and raw trace/log markers.
4. Add a run manifest example with placeholders only.
5. Define source-label and evidence-strength allowlists in one backend module and mirror them in schemas/tests.

Verification:

```bash
python3 scripts/validate_recruiter_evidence_dataset.py \
  --input datasets/synthetic/recruiter-evidence-qa.jsonl \
  --schema schemas/recruiter-evidence-qa.schema.json
```

```bash
python3 scripts/public_safety_scan.py \
  docs content datasets schemas scripts apps infra
```

### Phase 1 - Source Loader And Prompt Assembly

1. Load `content/profile.md` from the Lambda package or deployment artifact.
2. Enforce a 50 KB source cap with `PROFILE_SOURCE_MAX_CHARS`.
3. Sanitize role markers and model control-token patterns.
4. Assemble system instructions, `PUBLIC FACTS` delimiters, and recent conversation.
5. Fail closed on source overflow or sanitization failure.
6. Unit-test malicious source snippets with inert canaries such as `INJECTION_CANARY_DO_NOT_FOLLOW`.

Verification:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path("content/profile.md")
text = p.read_text(encoding="utf-8")
assert len(text) <= 51200, len(text)
print({"profile_chars": len(text)})
PY
```

```bash
cd apps/ryanprasad-chatbot/backend && pytest tests/test_sources.py tests/test_prompting.py
```

### Phase 2 - Backend Chat Lambda

1. Implement request parsing and validation for `POST /api/chat`.
2. Reconstruct server-side instructions and call Bedrock Converse.
3. Use `modelId=us.amazon.nova-2-lite-v1:0` by default.
4. Set `inferenceConfig.maxTokens=768`.
5. Use explicit SDK connect/read timeouts.
6. Parse the model answer into the response contract.
7. Validate citations and evidence strength against allowlists before returning.
8. Return generic failures for Bedrock or source-budget errors.

Verification:

```bash
cd apps/ryanprasad-chatbot/backend && pytest
```

```bash
python3 scripts/run_candidate_chatbot_eval.py \
  --dataset datasets/synthetic/recruiter-evidence-qa.jsonl \
  --mode local-contract
```

### Phase 3 - Rate Limits And API Surface

1. Add API Gateway HTTP API route `POST /api/chat`.
2. Add CORS allowlist for approved origins only.
3. Add per-route throttles.
4. Implement DynamoDB TTL counters for salted hashed IP/session windows.
5. Validate session ID shape, payload size, message count, and link count.
6. Return `429` without exposing internal counters.

Verification:

```bash
cd apps/ryanprasad-chatbot/backend && pytest tests/test_rate_limit.py
```

```bash
terraform -chdir=infra/terraform/ryanprasad-chatbot fmt -check
terraform -chdir=infra/terraform/ryanprasad-chatbot validate
```

### Phase 4 - Frontend SPA

1. Build the first screen as the chatbot itself.
2. Generate an opaque client-side `sessionId` and store it in local storage.
3. Add suggested prompt chips from the spec.
4. Display answer, citations, evidence strength, loading, retry, validation, rate-limit, and unavailable states.
5. Enforce the 2,000 character client-side input limit.
6. Avoid exposing AWS details or private config in frontend runtime variables.

Verification:

```bash
cd apps/ryanprasad-chatbot/frontend && npm install
cd apps/ryanprasad-chatbot/frontend && npm run build
```

### Phase 5 - Terraform Infrastructure

1. Create private S3 SPA bucket, CloudFront distribution, security headers, and SPA fallback.
2. Create API Gateway HTTP API and Lambda integration.
3. Create Lambda package wiring and environment variables.
4. Create DynamoDB TTL rate-limit table.
5. Create scoped IAM roles and policies.
6. Create KMS key placeholders and S3 lifecycle rules for lab/eval artifacts.
7. Add Bedrock invocation logging configuration for lab/eval mode where Terraform/provider support is current. If provider support lags AWS APIs, document the AWS CLI/API setup in `docs/security-preflight.md`.

Verification:

```bash
terraform -chdir=infra/terraform/ryanprasad-chatbot fmt -check
terraform -chdir=infra/terraform/ryanprasad-chatbot validate
```

```bash
python3 scripts/public_safety_scan.py infra/terraform/ryanprasad-chatbot
```

### Phase 6 - Bedrock Preflight

1. Implement `scripts/bedrock_preflight.py` as a wrapper around AWS SDK calls.
2. Verify selected Region, `ListFoundationModels`, `ListInferenceProfiles`, `GetInferenceProfile`, model access, quotas, and IAM.
3. Run a Converse smoke test with `maxTokens=16`.
4. Write a preflight JSON summary locally or to lab S3 only. Do not commit live outputs.
5. Record preflight status in the run manifest.

Verification:

```bash
python3 scripts/bedrock_preflight.py \
  --region us-east-1 \
  --model-id us.amazon.nova-2-lite-v1:0 \
  --max-tokens 768
```

### Phase 7 - Deterministic Eval Gates

1. Score every golden prompt in `datasets/synthetic/recruiter-evidence-qa.jsonl`.
2. Require supported answers to include allowlisted citations.
3. Reject nonexistent citations.
4. Reject private-source claims, local paths, unpublished details, and raw AWS details.
5. Reject production-customer evidence upgrades unless supported by `content/profile.md`.
6. Require unsupported/private prompts to refuse or say the public source does not support the claim.
7. Require the container-orchestration answer to include `aws-devops-lab` and `airgap-aiops` unless the source changes.

Verification:

```bash
python3 scripts/run_candidate_chatbot_eval.py \
  --dataset datasets/synthetic/recruiter-evidence-qa.jsonl \
  --mode deterministic \
  --fail-on citation,overclaim,private-source,refusal
```

### Phase 8 - BYOI Regression Batch

1. Generate chatbot responses for the golden dataset in lab/eval mode.
2. Keep raw Bedrock invocation logs in same-Region lab S3 only.
3. Normalize selected answers into BYOI model-eval JSONL.
4. Use AWS-documented BYOI row shape:
   - `prompt`
   - `referenceResponse`
   - `category`
   - `modelResponses[].response`
   - `modelResponses[].modelIdentifier`
5. Enforce one `modelResponses` entry per prompt and one unique `modelIdentifier` per Bedrock evaluation job unless current AWS docs say otherwise.
6. Validate the BYOI dataset locally before uploading to S3.

Verification:

```bash
python3 scripts/bedrock_byoi_adapter.py \
  --input s3://example-eval-bucket/eval-runs/<run_id>/normalized/chatbot-answers.jsonl \
  --output /tmp/bedrock-byoi.jsonl \
  --model-identifier ryanprasad-ai-chatbot-v1
```

```bash
python3 scripts/validate_recruiter_evidence_dataset.py \
  --input /tmp/bedrock-byoi.jsonl \
  --schema schemas/bedrock-model-eval-byoi.schema.json
```

### Phase 9 - Judge Calibration

1. Run the same BYOI judge batch at least 3 times.
2. Record evaluator model, rubric, metric set, dataset version, prompt/source version, and run IDs.
3. Compare judge labels against human labels for the golden dataset.
4. Flag high-variance prompts for human review.
5. Do not use judge scores as deploy blockers until agreement and variance are documented.
6. Keep raw judge outputs and provider responses in lab S3 only; commit only normalized summaries.

Verification:

```bash
python3 scripts/run_candidate_chatbot_eval.py \
  --dataset datasets/synthetic/recruiter-evidence-qa.jsonl \
  --mode judge-calibration \
  --runs 3 \
  --manifest schemas/examples/run-manifest.example.json
```

### Phase 10 - Rollout

1. Deploy to a preview origin first.
2. Run source hardening tests, backend tests, frontend build, Terraform validation, public-safety scan, Bedrock preflight, and deterministic evals.
3. Run manual smoke questions:
   - "Where does Ryan show container orchestration?"
   - "Did Ryan own a large production Kubernetes platform at a company?"
   - "What private projects or private notes support Ryan's skills?"
4. Confirm canonical answer includes `aws-devops-lab`, `airgap-aiops`, citations, and lab/public-project caveat.
5. Confirm unsupported/private-source questions refuse or state lack of public support.
6. Enable lab invocation logging only for regression runs; disable or tightly retain according to the runbook.
7. Promote CloudFront alias after checks pass.
8. Roll back by restoring the previous Lambda alias and previous SPA asset version.

## Required Local Verification Bundle

Run before opening a PR:

```bash
git diff --check
```

```bash
python3 -m json.tool schemas/examples/run-manifest.example.json >/dev/null
```

```bash
python3 - <<'PY'
import json
from pathlib import Path

path = Path("datasets/synthetic/recruiter-evidence-qa.jsonl")
required = {
    "id",
    "question",
    "expected_sources",
    "must_include",
    "must_not_claim",
    "expected_evidence_strength",
    "referenceResponse",
    "category",
}
for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
    row = json.loads(line)
    missing = required - row.keys()
    if missing:
        raise SystemExit(f"{path}:{line_no}: missing {sorted(missing)}")
print(f"validated {line_no} JSONL rows")
PY
```

```bash
python3 - <<'PY'
from pathlib import Path

for path in [
    Path("AGENTS.md"),
    Path("README.md"),
    Path("docs/ryanprasad-ai-chatbot.md"),
    Path("docs/aws-ai-evals-learning-plan.md"),
    Path("content/profile.md"),
    Path("datasets/synthetic/recruiter-evidence-qa.jsonl"),
]:
    assert path.exists(), path
print("required source specs present")
PY
```

After implementation exists, extend the bundle with:

```bash
python3 scripts/public_safety_scan.py docs content datasets schemas scripts apps infra
python3 scripts/validate_recruiter_evidence_dataset.py --input datasets/synthetic/recruiter-evidence-qa.jsonl --schema schemas/recruiter-evidence-qa.schema.json
cd apps/ryanprasad-chatbot/backend && pytest
cd apps/ryanprasad-chatbot/frontend && npm run build
terraform -chdir=infra/terraform/ryanprasad-chatbot fmt -check
terraform -chdir=infra/terraform/ryanprasad-chatbot validate
```

## Acceptance Criteria

- The public chatbot answers recruiter skills/project questions from `content/profile.md`.
- The canonical container-orchestration answer includes `aws-devops-lab`, `airgap-aiops`, source labels, and a lab/public-project caveat.
- Supported answers include allowlisted citations and evidence-strength labels.
- Unsupported and private-source questions refuse or say the public source does not support the claim.
- The backend fails closed on source budget overflow or source load/sanitize failure.
- Bedrock calls use Converse with explicit `maxTokens=768`.
- Bedrock preflight verifies model/profile availability, model access, quota, scoped IAM, and a smoke invocation.
- Rate limiting uses DynamoDB TTL counters with salted hashed IP/session keys and no raw IP storage.
- Bedrock invocation logging for lab/eval runs uses S3 only, KMS encryption, same-Region delivery, and lifecycle expiration.
- Deterministic eval gates pass before deploy.
- BYOI regression datasets validate locally and use AWS-documented `prompt`/`referenceResponse`/`category`/`modelResponses[].response`/`modelResponses[].modelIdentifier` shape.
- Judge calibration runs 3 times and is compared to human labels before judge scores become gates.
- No raw logs, provider responses, secrets, real AWS identifiers, private paths, private endpoints, or private personal data are committed.

## Risks And Checks

| Risk | Check |
| --- | --- |
| Source injection changes the assistant's instructions | Treat sources as facts, sanitize markers, wrap in `PUBLIC FACTS`, and test inert canaries. |
| Source grows beyond prompt budget | Enforce 50 KB cap and fail closed instead of truncating. |
| Bot overclaims lab evidence as production evidence | Deterministic overclaim scorer plus human review of golden prompts. |
| Citation theater | Citation allowlist and required citations for material claims. |
| Bedrock model/profile unavailable or inaccessible | Run preflight before deploy and fail closed by default. |
| AWS docs drift | Re-check official docs before coding schemas, IAM, invocation logging, metrics, and quotas. |
| Raw model I/O leaks into repo | S3-only lab logs, lifecycle, KMS, public-safety scan, and no committed provider responses. |
| Public abuse burns quota | API Gateway throttles, DynamoDB TTL counters, payload caps, and generic 429s. |
| LLM judge variance hides regressions | 3x judge runs, human labels, variance review, deterministic gates first. |
| Frontend exposes internals | Keep all AWS config, source paths, and runtime prompts server-side. |

## Two Design Questions To Keep Honest

1. Which source label proves this answer, and does that source support the strength of the claim?
2. If this artifact were accidentally published, would it still be safe and boring?
