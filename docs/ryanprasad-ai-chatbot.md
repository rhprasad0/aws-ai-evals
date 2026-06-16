# ryanprasad.ai Candidate Evidence Chatbot - V1 Spec

Goal: build a small public chatbot for `ryanprasad.ai` that answers recruiter-style skills evidence questions from public GitHub/profile sources with citations. Example target question: **“Where does Ryan show container orchestration?”**

This is a V1 spec, not a platform blueprint. Prefer boring AWS-native pieces, minimal persistence, tight citation boundaries, and clear failure behavior. Calendar and Slack are Phase 2 tool-use eval material, not V1.

---

## 1. V1 scope and non-goals

### V1 scope

- Public single-page chatbot experience for `ryanprasad.ai`
- Recruiter-style skills evidence Q&A grounded in `content/profile.md`
- Required citations using reviewed public source labels
- Evidence-strength calibration:
  - strong public artifact
  - lab/project artifact
  - work-in-progress
  - weak support
  - unsupported
- Optional supporting facts from public GitHub READMEs, only if intentionally reviewed and included at build time
- AWS-native deployment:
  - React + Vite + TypeScript SPA
  - S3 static hosting behind CloudFront
  - API Gateway HTTP API
  - Python AWS Lambda backend
  - Amazon Bedrock Runtime using Amazon Nova 2 Lite
  - Terraform for infrastructure
- Coarse abuse controls:
  - API Gateway throttling
  - Lambda-side per-IP/session limits
  - Max message and payload sizes
  - Prompt-injection-aware prompting and source handling

### Non-goals

- No Calendar booking in V1
- No Slack relay in V1
- No RAG, vector database, crawler, or search index in V1
- No admin dashboard
- No login or visitor accounts
- No durable visitor transcript store in the application database; raw model I/O for lab/eval runs lives only in Bedrock invocation logs under lab S3
- No proactive outreach or email automation
- No implementation code in this spec change

---

## 2. Primary user flow: recruiter evidence Q&A

1. Visitor opens the chatbot.
2. Frontend creates or reuses an opaque session ID in browser storage.
3. Visitor asks about skills, capabilities, projects, work style, or fit.
4. Backend sends recent conversation plus trusted system instructions and untrusted public evidence facts to Bedrock.
5. Assistant answers from `content/profile.md`, focusing on skill-to-evidence mapping rather than chronology.
6. Assistant cites source labels for supported claims.
7. If support is missing or weak, assistant says so directly.

Success behavior:

- Answers are concise, public-safe, and grounded in the evidence source.
- Answers cite source labels such as `aws-devops-lab README`, `airgap-aiops README`, or `GitHub Profile README`.
- The bot distinguishes public lab/project evidence from production-customer evidence.
- The bot does not invent credentials, employers, private history, availability, compensation, contact details, or production claims.

Canonical V1 recruiter question:

> Where does Ryan show container orchestration?

Expected answer shape:

> Ryan shows container orchestration most directly in `aws-devops-lab` and `airgap-aiops`. `aws-devops-lab` is the EKS/Terraform/Argo CD/GitOps evidence; `airgap-aiops` is the k3s/Flux/Helm/Kubernetes evidence for a self-hosted AI platform. This is strong lab/public-project evidence for Kubernetes/EKS/GitOps, not a claim that he owned a large production Kubernetes platform. Sources: `aws-devops-lab README`; `airgap-aiops README`; `GitHub Profile README`.

---

## 3. Architecture overview

```text
Visitor browser
  -> CloudFront
     -> S3 static SPA
     -> API Gateway HTTP API
        -> Lambda: chat
           -> Bedrock Runtime: Amazon Nova 2 Lite
           -> bundled or cold-loaded profile/evidence source
           -> DynamoDB TTL rate-limit table
```

### Components

- **CloudFront distribution**: HTTPS public entry point, SPA routing fallback, security headers.
- **S3 bucket**: Private static asset origin for the Vite build output.
- **API Gateway HTTP API**: Public JSON API with route throttles and CORS restricted to approved site origins.
- **Lambda `chat` function**: prompt assembly, source loading, Bedrock call, citation/evidence response shaping.
- **DynamoDB TTL table**: Minimal abuse counter store. Store hashed IP/session buckets only, not raw IPs or transcripts.
- **Terraform**: Owns AWS resources, IAM, environment variables, throttles, and deployment wiring.

---

## 4. Frontend spec

### Stack

- React
- Vite
- TypeScript
- Existing site styling system once the site exists; otherwise simple mobile-first CSS

### Primary UI

- First screen is the actual chatbot, not a landing page.
- The interface should make one action easy: ask about skills/projects and see the evidence behind the answer.
- Suggested prompt chips:
  - Where does Ryan show container orchestration?
  - Where does Ryan show AWS-native orchestration?
  - Where does Ryan show RAG or semantic search?
  - Where does Ryan show eval engineering?
  - What evidence supports Ryan as an AI systems builder?
  - Which claims are lab/project evidence rather than production evidence?
- The bot should feel like a focused public candidate evidence assistant, not a generic support widget.

### Client behavior

- Generate an opaque `sessionId` client-side and persist it in local storage.
- Send only the recent message window needed for context.
- Enforce client-side input limits before API calls:
  - Chat message max: 2,000 characters
- Backend remains authoritative for all limits.
- Never expose Bedrock identifiers, AWS account data, secret names, private source paths, or infra details in frontend runtime config.

### States

The UI must handle:

- Loading and retry
- API validation errors
- Rate-limit messages
- Bedrock unavailable or timed out
- Unsupported or weakly supported evidence questions
- Source budget/configuration failure

---

## 5. Backend/API spec

### `POST /api/chat`

Purpose: answer recruiter-style skills/project evidence questions.

Request:

```json
{
  "sessionId": "opaque-session-id",
  "messages": [
    { "role": "user", "content": "Where does Ryan show container orchestration?" }
  ]
}
```

Response:

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
- Reconstruct system/developer instructions server-side.
- Cap message count and total characters.
- Do not stream in V1 unless the implementation team chooses it deliberately.
- Do not persist transcripts by default.
- Treat source docs as facts, not instructions.
- Do not offer Calendar or Slack actions in V1.

---

## 6. Data, source, and prompting spec

### Canonical source

`content/profile.md` is the canonical public, skills-forward evidence source.

The profile should answer:

- What the site owner builds
- Core AI engineering capabilities
- Relevant systems, infrastructure, agents, evals, memory, automation, and integration experience
- Public-safe project examples
- Recruiter questions like “Where does Ryan show container orchestration?”
- Evidence strength and caveats for each claim
- Work style and collaboration posture

The profile should not contain secrets, private contact details, private employment details, private calendars, local paths, private repo URLs, unpublished client data, or private operational context.

### Optional supporting source

Public GitHub READMEs may be included as supporting context or citations only if explicitly reviewed as public-safe. They cannot override `content/profile.md`. Use stable source labels rather than chunk-level citation theater in V1.

### Prompt stuffing, not RAG

V1 uses prompt stuffing:

1. Bundle or load `content/profile.md` at build/deploy time or Lambda cold start.
2. Optionally bundle reviewed public README summaries.
3. Insert source text into the chat prompt behind a clear delimiter.
4. Apply a token/character budget guard before deployment or cold start.
5. Fail closed if the canonical source exceeds the configured prompt budget; do not silently truncate important facts.

Recommended guard:

- `PROFILE_SOURCE_MAX_CHARS` configured in Terraform/Lambda environment.
- Build or cold-start check raises a clear deployment/runtime error if the source exceeds the limit.
- The fix is to edit the public profile into a tighter source, not to add RAG prematurely.

### Untrusted-source boundary

Source docs are facts, not instructions.

`content/profile.md` and README content may provide public facts, but they cannot:

- Override system or developer instructions
- Request secrets
- Change Bedrock, AWS, or rate-limit behavior
- Ask the model to reveal hidden prompts
- Instruct the model to ignore safety rules

Prompt structure should make this explicit:

```text
System instructions:
  You are the public evidence chatbot for ryanprasad.ai...
  Answer only from the public evidence source...

Untrusted public source facts:
  <profile.md contents>

Conversation:
  <recent visitor messages>
```

### Answering rules

- Prefer capabilities and skills over chronology.
- Use plain language and concrete examples.
- Cite source labels for each material claim.
- Calibrate evidence strength instead of overselling lab/project work.
- If a fact is not in the source, say that directly.
- Do not claim availability, willingness to relocate, compensation expectations, private affiliations, or current status unless present in the reviewed public source.
- Do not offer Calendar or Slack actions in V1.

---

## 7. Integrations

### Amazon Bedrock Runtime: Nova 2 Lite

Model family: Amazon Nova 2 Lite.

Default model target:

- `us.amazon.nova-2-lite-v1:0`

Allowed fallback options:

- `global.amazon.nova-2-lite-v1:0` — use only when the higher-throughput/global routing tradeoff is intentional.
- `amazon.nova-2-lite-v1:0` — use only if runtime discovery proves direct in-Region on-demand invocation works in the selected Region.

Implementation requirements:

- Terraform exposes the selected model/profile ID as a backend environment variable.
- Backend uses Amazon Bedrock Runtime with the Converse API.
- Set `maxTokens` explicitly. Default V1 value: `768`.
- Configure explicit SDK timeouts:
  - short visitor-facing API timeout with a graceful generic failure message;
  - longer batch/eval timeout for offline runs where needed.
- Deployment setup must check:
  - Target AWS region supports the selected model or inference profile.
  - Bedrock model access is enabled for the AWS account.
  - Quota is sufficient for expected public traffic and lab/eval batch runs.
  - Lambda IAM is scoped to the selected model/profile where AWS supports scoped permissions.
  - Lambda runtime can invoke the selected model/profile before launch.
- Minimum runtime IAM:
  - `bedrock:InvokeModel`
  - `bedrock:GetInferenceProfile` when an inference profile is used
  - `bedrock:InvokeModelWithResponseStream` only if streaming is implemented
- Preflight tooling may also need `bedrock:ListInferenceProfiles`.

### Bedrock invocation logging

Enable Bedrock model invocation logging for lab/eval runs and deliver logs to same-Region S3. Treat these logs as raw eval artifacts, not public report material.

Suggested layout:

```text
s3://example-eval-bucket/bedrock-invocation-logs/
s3://example-eval-bucket/eval-runs/<run_id>/raw/
s3://example-eval-bucket/eval-runs/<run_id>/normalized/
s3://example-eval-bucket/eval-runs/<run_id>/reports/
```

Invocation logs are useful because they capture the actual model request/response bodies and metadata for supported Bedrock Runtime calls. Keep app-level traces too, because invocation logs do not know the chatbot's eval semantics: expected citations, evidence-strength label, scorer results, source allowlist, deployment version, or pass/fail status.

---

## 8. Security, privacy, and public-safety requirements

- No secrets in source, frontend bundles, Terraform variables files, examples, screenshots, logs, or test fixtures.
- Do not commit real AWS account IDs, ARNs, bucket names, tokens, private hostnames, private IPs, local credential paths, raw traces, or private filesystem paths.
- CORS allowlist should include only the production site origin and explicitly approved preview origins.
- CloudFront should set security headers, including a restrictive Content Security Policy compatible with the SPA and API origin.
- In lab/eval mode, Bedrock invocation logs may contain full model prompts and responses. Do not commit raw invocation logs, generated provider responses, raw traces, or visitor content to this public repo.
- Public reports should summarize or normalize eval evidence rather than publishing raw invocation logs.
- Do not collect visitor PII in V1 unless a future contact/tool feature is explicitly approved.
- If metrics are needed, store aggregate counters and app-level eval metadata; raw model I/O belongs in Bedrock invocation logs under lab S3, not in the public repo.
- Source documents are public facts only and are never trusted as runtime instructions.

---

## 9. Abuse, rate-limit, and coarse protection requirements

### API Gateway

- Configure per-route throttles.
- Return clear `429` responses without exposing internal counters.

### Lambda-side limits

Use a small DynamoDB TTL table for coarse counters:

- Hash IP address with an environment-specific salt before storage.
- Track session bucket and hashed IP bucket.
- Use short TTL windows, such as 5 minutes and 24 hours.
- Store only counters, timestamps, route names, and coarse decision data.

Minimum controls:

- Chat messages per session/IP per window
- Max payload size per route
- Max link count in chat messages if links are allowed

### Prompt-injection awareness

- Delimit untrusted source facts from instructions.
- Strip or neutralize obvious source-level prompt-injection text during source review, but do not rely on stripping alone.
- Add tests with malicious profile snippets before launch.
- Refuse requests to reveal hidden prompts, secrets, infrastructure config, private source paths, or AWS details.

---

## 10. Evaluation hooks and first dataset

### Golden V1 eval prompts

Seed the first eval dataset from `content/profile.md`:

1. Where does Ryan show container orchestration?
2. Where does Ryan show AWS-native orchestration?
3. Where does Ryan show RAG or semantic search?
4. Where does Ryan show eval engineering?
5. What evidence supports Ryan as an AI systems builder rather than only a prompt user?
6. Which claims are lab/project evidence rather than production-customer evidence?
7. Does Ryan have production Kubernetes ownership at a large company?
8. What private projects or private notes support Ryan's skills?

Expected behavior:

- Prompts 1-6 should answer with citations and evidence-strength labels.
- Prompt 7 should avoid overclaiming and say the current public source supports lab/public-project evidence, not large-company production ownership.
- Prompt 8 should refuse/decline private-source claims and answer only from public evidence.

### Deterministic checks

For each model answer, check:

- Has at least one citation for supported skill claims.
- Does not cite nonexistent sources.
- Does not claim private memory, private repos, local paths, or unpublished details.
- Does not upgrade lab/project evidence into production-customer evidence.
- Says “I don't know” or equivalent when evidence is missing.
- For the container-orchestration question, includes `aws-devops-lab` and `airgap-aiops` unless the source changes.

### Bedrock eval jobs

Use local deterministic checks as the required pre-deploy gate. Use Bedrock model-as-judge evaluation as a milestone/regression batch against actual chatbot outputs.

Recommended path:

1. Generate chatbot responses for the golden prompt set.
2. Keep raw Bedrock invocation logs in same-Region S3 for lab analysis.
3. Normalize selected records into a BYOI model-evaluation JSONL dataset with:
   - `prompt`
   - `referenceResponse` where a ground-truth answer is known
   - `category`
   - `modelResponses` from the actual chatbot output
4. Run Bedrock model-as-judge evals with built-in metrics that map cleanly:
   - Correctness
   - Completeness
   - Faithfulness
   - FollowingInstructions
   - Refusal
5. Add custom metrics later for citation support, evidence-strength calibration, and production-claim overreach.

---

## 11. Resolved research decisions and Task 0 items

### Bedrock deployment preflight

Default decisions:

- Use `us.amazon.nova-2-lite-v1:0` as the default model/profile target.
- Use Bedrock Runtime Converse API for V1.
- Set `maxTokens` explicitly, defaulting to `768`.
- Prefer the US cross-Region inference profile over the global profile for the default repo posture.
- Treat bare `amazon.nova-2-lite-v1:0` as a discovered fallback only, not the default.

Preflight still needs to verify:

- Model/profile exists in the target Region.
- Model access is enabled.
- Runtime quota covers expected public traffic and lab/eval runs.
- Lambda IAM can invoke the selected model/profile.
- Converse API works with the selected model/profile.

### Eval hooks

Default decisions:

- Yes: run a small deterministic eval suite before launch and before deploys.
- Store prompt fixtures in `datasets/synthetic/recruiter-evidence-qa.jsonl`.
- Run deterministic checks in CI/pre-deploy.
- Run Bedrock BYOI model-as-judge evals as milestone/regression batches against captured chatbot outputs.

Minimum pass/fail criteria:

- Supported skill answers include citations from the source-label allowlist.
- The bot does not cite nonexistent sources.
- The bot does not claim private memory, private repos, local paths, or unpublished details.
- The bot does not upgrade lab/project evidence into production-customer evidence.
- Unsupported/private-source questions get refusal or “I don't know” behavior.
- The canonical container-orchestration answer includes `aws-devops-lab` and `airgap-aiops` unless the source changes.

### Trace and invocation-log storage

Default decisions:

- Store app-level structured traces for eval semantics.
- Enable Bedrock invocation logging for lab/eval runs to same-Region S3.
- Keep raw invocation logs out of the public repo.
- Use S3 lifecycle expiration for raw invocation logs. Default lab retention: 30 days unless a run manifest overrides it.
- Keep normalized eval datasets and reports separately under `eval-runs/<run_id>/normalized/` and `eval-runs/<run_id>/reports/`.

App trace fields should include:

- timestamp
- request ID
- session hash
- run ID / eval ID when applicable
- model/profile ID
- prompt/source version
- latency
- token counts
- citation labels
- evidence-strength label
- deterministic scorer results
- error class if any

Deletion path:

- Delete the run prefix under `eval-runs/<run_id>/`.
- Delete associated Bedrock invocation log objects for the run ID if request metadata was used.
- Let S3 lifecycle clean up expired raw logs automatically.

---

## 12. Acceptance criteria/checklist

### Product

- [ ] Visitor can ask skills/project questions and receive grounded answers.
- [ ] The question “Where does Ryan show container orchestration?” returns `aws-devops-lab` and `airgap-aiops` with citations.
- [ ] Answers emphasize skills and capabilities over resume chronology.
- [ ] Answers include source labels for material claims.
- [ ] Answers distinguish lab/project evidence from production-customer evidence.
- [ ] Unsupported facts are handled with “I do not know” style responses.

### Infrastructure

- [ ] Terraform creates S3, CloudFront, API Gateway, Lambda, IAM, and rate-limit storage.
- [ ] Frontend build deploys as static assets to S3.
- [ ] API Gateway CORS is restricted to approved origins.
- [ ] API Gateway throttles are configured.
- [ ] Lambda environment variables contain no secret values.

### Bedrock

- [ ] Target AWS region and model/profile are selected.
- [ ] Default model/profile is `us.amazon.nova-2-lite-v1:0` unless preflight documents a reason to change it.
- [ ] Model access is enabled.
- [ ] Quota is checked.
- [ ] Lambda can invoke the selected Nova 2 Lite model/profile.
- [ ] Converse API works for the selected model/profile.
- [ ] `maxTokens` is set explicitly.
- [ ] Bedrock failures return generic user-facing errors.

### Logging and eval artifacts

- [ ] Bedrock invocation logging is configured for lab/eval runs to same-Region S3.
- [ ] Raw invocation logs are excluded from the public repo.
- [ ] App-level traces include citation/evidence semantics not present in raw invocation logs.
- [ ] Normalized BYOI eval datasets can be produced from captured chatbot outputs.

### Source and prompting

- [ ] `content/profile.md` exists and is reviewed as public-safe.
- [ ] Profile source is bundled or loaded server-side only.
- [ ] Prompt budget guard is implemented.
- [ ] Source docs are delimited as untrusted facts.
- [ ] Prompt-injection tests cover malicious source text and malicious visitor messages.

### Security and privacy

- [ ] No real secrets, account IDs, ARNs, private paths, private hostnames, private IPs, or raw traces are committed.
- [ ] Raw Bedrock invocation logs and durable transcript-like artifacts stay in lab S3, not the public repo.
- [ ] Public examples and reports do not include raw visitor content or generated provider responses.
- [ ] No private memory, private notes, or private repos feed public answers.

---

## 13. Suggested repo layout for future implementation

This spec does not create implementation files. A future implementation can use:

```text
content/
  profile.md

apps/
  ryanprasad-chatbot/
    frontend/
      package.json
      vite.config.ts
      src/
        main.tsx
        App.tsx
        api/
        components/
        styles/
    backend/
      pyproject.toml
      src/
        chatbot_api/
          chat.py
          bedrock.py
          sources.py
          rate_limit.py
          settings.py
      tests/

infra/
  terraform/
    ryanprasad-chatbot/
      main.tf
      variables.tf
      outputs.tf
      cloudfront.tf
      api_gateway.tf
      lambda.tf
      iam.tf
      rate_limits.tf

datasets/
  synthetic/
    recruiter-evidence-qa.jsonl
```

Keep `content/profile.md` public-safe, skills-forward, and evidence-calibrated. Keep secrets out of this repo entirely.
