# AWS AI Evals: 12-Week Hands-On Learning Plan

This is a learning-by-doing path for building an AWS-native and hybrid AI evaluation harness around a real production experiment: a public **ryanprasad.ai candidate evidence chatbot**. The goal is not to click around the Bedrock console and declare victory. The goal is to build a small but serious reference architecture: security and access preflight, datasets, schemas, validators, managed Bedrock eval jobs, AgentCore agent/tool evals, Inspect AI custom evals, orchestration, observability, quota-based cost controls, and public-safe reports.

Bedrock Evaluations and AgentCore Evaluations give you managed scoring, comparison, and reporting workflows. The harness you build around them handles preflight, validation, versioning, CI/CD glue, unsupported scorers, normalized exports, and public-safe evidence beyond the managed outputs.

## Production Experiment: ryanprasad.ai Candidate Agent

The live specimen is a public chatbot exposed on `ryanprasad.ai`. It should:

- answer recruiter-style questions about Ryan's public GitHub projects from public/project-safe sources, with citations;
- map skills to public evidence, starting with questions like “Where does Ryan show container orchestration?”;
- distinguish strong evidence, lab/project evidence, weak support, and unsupported claims;
- refuse unsupported, private, unsafe, or ambiguous requests.

RAG stays first: project Q&A is the main user value and the easiest place to build citation-backed evidence. Calendar booking and Slack relay are deferred Phase 2 tool-use flows; V1 keeps the app boring so the eval harness is the main work.

Product boundaries:

- No private memory, Honcho, Graphiti, local notes, private transcripts, or private repo content may appear in public answers unless explicitly curated into public-safe docs.
- No Calendar or Slack writes in V1.
- GitHub/project Q&A must cite public sources and say "I don't know" when support is missing.
- Evidence strength must be explicit: public artifact, lab/project artifact, WIP, weak support, or unsupported.

## North Star

By the end of 12 weeks, you should have a deployable **AWS Eval Harness Reference Architecture** that can:

- evaluate the `ryanprasad.ai` candidate evidence chatbot across public project Q&A, citation support, evidence calibration, refusal, and abuse-handling flows;
- evaluate model outputs with Amazon Bedrock Evaluations;
- evaluate RAG retrieval and retrieve-and-generate pipelines;
- evaluate agent/tool behavior with Amazon Bedrock AgentCore Evaluations;
- run programmatic and custom evals with Inspect AI on AWS;
- validate BYOI datasets before jobs run;
- compare judge scores against human labels;
- coordinate repeatable runs through Step Functions or an equivalent workflow where managed jobs need preflight, versioning, CI/CD, or cross-service glue;
- verify Region, model access, IAM service roles, S3/KMS, CloudWatch, quotas, and cost estimates before submitting jobs;
- store inputs, outputs, manifests, metrics, reports, and usage/cost evidence in S3;
- query results with Athena/Glue or equivalent tooling;
- publish public-safe evidence without leaking prompts, traces, credentials, account details, or private data.

What it is **not**: a universal benchmark runner, a correctness oracle, a safety certificate, proof of production readiness, or a full production platform. The managed Bedrock lanes provide native reports and S3 artifacts you still have to validate, govern, summarize where needed, and interpret for your scenario. The harness is the part you own.

## Working Assumptions

Use placeholders and synthetic data throughout:

- AWS account: `<AWS_ACCOUNT_ID>`
- Region: `us-east-1`
- Example bucket: `s3://example-eval-bucket/...`
- Public experiment domain: `ryanprasad.ai`
- Example non-product domain: `example.com`

Do not commit live AWS account IDs, ARNs, bucket names, CloudWatch log output, private traces, local paths, private IPs, Slack IDs, emails, calendar IDs, private hostnames, raw production traces, or secrets.

**Synthetic is not the same as safe.** The safety, refusal, and prompt-injection lanes (Weeks 5 and 8) generate *attacks* by design. In a public, billboard-safe repo, keep that content non-operational: name the attack class and use inert canaries (e.g. `INJECTION_CANARY_DO_NOT_FOLLOW`), never working jailbreaks, exploit code, or copy-pasteable harmful instructions. The rules above keep *real* data out; this one keeps *dangerous* content out. An eval repo must not double as an attack cookbook.

### Terms and source of truth

- **BYOI = Bring Your Own Inference responses.** For Bedrock model evaluation BYOI, you supply `modelResponses` in AWS's expected dataset shape. Amazon Bedrock skips the model-invoke step and evaluates the supplied responses. For V1, generate chatbot answers first, keep raw Bedrock invocation logs in same-Region S3 for lab analysis, and normalize selected outputs into BYOI datasets. Do not assume a Bedrock model-eval job directly calls arbitrary live endpoints unless the current AWS docs say so for that exact path.
- **The Source Ledger is the source of truth.** This plan paraphrases AWS schemas, field names, metric lists, job constraints, and evaluation modes so you can build against them — but AWS evolves these, and paraphrases drift. Confirm specifics against the linked docs before wiring anything up. When this plan and the docs disagree, the docs win.

## Architecture Lanes

Treat these as separate lanes that converge in the capstone:

1. **Model evaluation lane** — Bedrock model evaluation jobs, model-as-judge, built-in metrics, custom metrics, BYOI model responses.
2. **RAG evaluation lane** — Bedrock Knowledge Base retrieval-only and retrieve-and-generate evaluation for Ryan's public/project-safe GitHub corpus, native comparison/reporting for supported RAG sources/configurations, plus custom RAG BYOI datasets where you supply supported response data.
3. **Agent/tool evaluation lane** — deferred Phase 2. If Calendar or Slack tools are added later, evaluate tool choice, arguments, consent, and refusal behavior with AgentCore-compatible traces and supported evaluation modes.
4. **Custom harness lane** — Inspect AI, deterministic scorers, schema validators, custom task runners, SageMaker/ECS/Batch execution.
5. **Platform lane** — S3, KMS, IAM, Step Functions, small Lambda glue, CloudWatch, CloudTrail, Athena/Glue, Service Quotas, Cost Explorer/Budgets, CI/CD.

Lanes 1–4 are the **evaluation lanes**; lane 5 is cross-cutting glue. Lanes 1–3 lean on *managed* Bedrock and AgentCore jobs — you own preflight, dataset and trace preparation, manifesting, validation, and interpretation; AWS owns the supported scoring/reporting runtime. Start with native Bedrock comparison and reporting workflows where they fit. Add custom orchestration for preflight, versioning, CI/CD, unsupported scorers, repeated-run analysis, cross-service aggregation, and reporting beyond managed outputs. Lane 4 is code you run yourself. Keep their datasets, schemas, and result shapes separate; they only converge at the orchestration and reporting layer, and a score from one lane does not transfer to another.

## Managed Job Boundaries (Read Before Week 4)

Bedrock model, RAG, and AgentCore evaluations are *managed jobs*, not a magic verdict service. Before you lean on them, internalize the edges:

- **They run in your account, on your data.** Jobs read inputs from and write outputs to *your* S3, under a service role you scope. Your dataset content flows to the evaluator model. Results come back as managed reports and S3 artifacts that you must govern, validate, retain, and interpret for your scenario.
- **Use native comparison/reporting first.** Bedrock Evaluations has managed reports and comparison workflows for supported model, configuration, and RAG evaluation paths. If the specific API or BYOI path you choose is scoped to one model, response source, or RAG source, record that boundary in the manifest and coordinate separate jobs only where needed.
- **The judge is a versioned dependency you do not control.** Evaluator model, rubric, and AWS defaults can change underneath you. Pin and record them; re-baseline when they move.
- **Availability varies — and availability is not access.** Evaluator models, metrics, and eval features are not uniform across regions or models; confirm availability for your region before you design around a feature. Available is also not enabled: whichever models the job invokes (the evaluator always, the candidate unless you brought BYOI responses) must have model access granted in your account, or the job dies at a permissions wall instead of a friendly hint.
- **Quotas and limits are real.** Prompt counts, dataset sizes, concurrent jobs, and model token throughput are bounded — confirm current quotas and estimate token/cost impact before job submission, not after a runaway run has started. Set `maxTokens` explicitly so Bedrock does not reserve far more output-token quota than the chatbot needs.
- **Managed scoring still is not ground truth.** A model-as-judge job measures with error; deterministic checks and human labels keep it honest.

## Repository Shape to Build Toward

```text
aws-ai-evals/
  README.md
  AGENTS.md
  docs/
    aws-ai-evals-learning-plan.md
    evaluability-design-doc.md
    architecture.md
    runbook.md
    reports/
  schemas/
    model-eval-byoi.schema.json
    rag-retrieve-generate-byoi.schema.json
    agent-trace-export.schema.json
    run-manifest.schema.json
  datasets/
    synthetic/
      model-prompts.jsonl
      project-qa-rag.jsonl
      recruiter-evidence-qa.jsonl
      unsupported-private-info.jsonl
      human-labels.jsonl
  src/
    adapters/
    validators/
    scorers/
    manifests/
  infra/
    cdk/ or terraform/
    step-functions/
    iam/
  inspect/
    recipes/
    tasks/
  agentcore/
    evaluators/
    trace-examples/
  scripts/
    public_safety_scan.py
    validate_dataset.py
    summarize_run.py
```

This plan starts documentation-first, then turns it into code and deployable infrastructure.

---

## Week 1 — Candidate Agent Design, Security Envelope, and Repo Contracts

### Objective

Define the public `ryanprasad.ai` candidate evidence chatbot as the specimen: recruiter evidence intents, citation rules, safety boundaries, success criteria, threat model, secrets/IAM, and public/private data boundaries.

### Why it matters

Most eval systems fail because the app was never instrumented for evaluation, or because IAM, KMS, model access, Region, quota, and retention decisions get bolted on after sensitive artifacts already exist. For a public recruiter chatbot, the trap is subtler: it can inflate lab work into production claims, cite nonexistent sources, or leak private context. Capture raw Bedrock invocation logs for lab/eval runs, and capture app-level source labels, evidence strength, refusals, errors, run parameters, and security boundaries consistently or you get vibes in a trench coat instead of evidence.

### AWS services/docs to study

- Amazon Bedrock Evaluations overview
- Bedrock model access, supported models, Region availability, and Service Quotas
- Bedrock model/RAG evaluation IAM service role and KMS requirements
- Bedrock and AgentCore data protection/encryption docs
- Bedrock model invocation logging
- CloudWatch Logs, S3, CloudTrail, KMS, IAM, Secrets Manager, and WAF basics

### Build tasks

1. Write `docs/evaluability-design-doc.md` with the candidate-agent contract:
   - visitor intents: recruiter public project Q&A, skill-to-evidence mapping, unsupported/private-info questions, abuse/spam;
   - success criteria by intent;
   - expected failure modes;
   - threat model for prompt injection, spam, data leakage, citation fabrication, evidence inflation, and unsupported claims;
   - public/private data boundary, including "public GitHub/project-safe sources only" for answers;
   - rule that no Honcho, Graphiti, private memory, private notes, transcripts, or private repos feed public answers unless explicitly curated into public-safe docs;
   - trace schema draft for chat turns, Bedrock invocation-log references, source labels, evidence strength, refusals, latency, token/cost usage, and error fields;
   - privacy/safety policy;
   - region pinning and data residency policy;
   - dataset classification and sanitization policy;
   - retention policy for S3 raw invocation logs, normalized eval artifacts, CloudWatch Logs, and local artifacts;
   - cross-region replication restrictions;
   - quota-based cost control plan;
   - AWS/service/tool responsibility split.
2. Write an AWS security/access preflight note in `docs/evaluability-design-doc.md` or `docs/security-preflight.md` covering:
   - selected AWS Region and why eval data must stay there;
   - S3 bucket layout, object ownership, versioning, lifecycle, and replication disabled unless explicitly approved;
   - customer-managed KMS key placeholders for eval inputs, outputs, CloudWatch exports, and managed job encryption where supported;
   - per-lane service roles for Bedrock model eval, RAG eval, AgentCore, Inspect/SageMaker, ECS/Batch, and Step Functions;
   - no V1 tool writes; Calendar and Slack remain Phase 2 only;
   - no tool secrets, OAuth tokens, calendar IDs, Slack destinations, or AWS details in browser code;
   - model access verification for every generator and evaluator model before job creation;
   - default chatbot model/profile `us.amazon.nova-2-lite-v1:0`, with `global.amazon.nova-2-lite-v1:0` only as an intentional fallback;
   - Converse API as the default Bedrock Runtime API;
   - explicit `maxTokens` default of `768` for V1 chatbot calls;
   - Service Quotas checks for concurrent jobs and model token throughput;
   - spam/rate-limit controls for chat sessions;
   - pre-submit cost estimation that multiplies prompts, candidate configs, evaluator runs, repeated-run calibration, and max output tokens;
   - retention windows for managed outputs, CloudWatch log groups, Athena tables, production trace exports, and public reports.
3. Define a run manifest format with fields for:
   - candidate agent version;
   - dataset version;
   - prompt version;
   - public corpus/index version;
   - citation policy version;
   - evidence-strength taxonomy version;
   - model/provider ID and pinned model version (an alias can move under you);
   - inference parameters, including explicit `maxTokens`;
   - scorer versions;
   - judge model/rubric versions;
   - random seed where applicable (note that hosted models may ignore it and are not guaranteed deterministic);
   - code commit;
   - AWS region;
   - service role ID placeholder;
   - KMS key ID placeholder;
   - model access preflight status;
   - quota estimate and approval status;
   - rate-limit configuration version;
   - cost estimate before job submission;
   - run timestamp.
4. Draft a public-safe evidence policy:
   - what can be committed;
   - what must stay in S3 only;
   - what must stay in lab S3 only, including raw Bedrock invocation logs;
   - how public reports summarize or normalize evidence without committing raw provider responses;
   - how lab traces and invocation logs are linked to run IDs, retained, and expired.
5. Sketch the candidate-agent and eval-harness architecture in `docs/architecture.md`.
6. Write `schemas/run-manifest.schema.json` and a matching `schemas/examples/run-manifest.example.json` that validates against it, so Week 1 ships a checkable artifact, not just prose.

### Validation checks

- A new contributor can explain what the chatbot does, what it refuses, and why those behaviors are evaluated.
- Every planned artifact has a safe storage location.
- IAM/KMS/Region/model-access/quota/cost controls exist before dataset work begins, including the selected Nova 2 Lite inference profile and explicit `maxTokens`.
- Model access is explicitly checked for both generator and evaluator models in the chosen Region.
- Data residency is explicit: no accidental cross-region replication, unmanaged CloudWatch retention, or public artifact pipeline for sensitive outputs.
- No Calendar or Slack writes exist in V1.
- GitHub/project Q&A cites public sources and says "I don't know" when unsupported.
- The canonical container-orchestration question returns `aws-devops-lab` and `airgap-aiops` with caveats.
- The design separates model, RAG, agent, and custom harness lanes while keeping one live specimen.
- No live AWS identifiers, private examples, raw traces, real emails, Slack IDs, calendar IDs, private hostnames, or secrets are present.
- The example run manifest validates against `schemas/run-manifest.schema.json`.
- Reproducibility is scoped honestly: the manifest pins versions and parameters, but the doc states plainly that hosted models may not reproduce token-for-token.

### Public-safe artifacts to commit

- `docs/evaluability-design-doc.md`
- `docs/architecture.md`
- `docs/security-preflight.md` if you keep the security envelope separate
- `schemas/run-manifest.schema.json`
- `schemas/examples/run-manifest.example.json`
- `scripts/public_safety_scan.py`

### Common failure modes

- Treating Bedrock Evaluations as the whole harness.
- Treating the public chatbot as a demo while the eval plan studies a different synthetic app.
- Skipping privacy design until traces contain visitor content.
- Forgetting that model invocation logging captures the raw model I/O you actually need for eval debugging, while still treating its S3 destination as lab artifact storage rather than public repo material.
- Starting dataset work before you know which Region, KMS keys, service roles, model access grants, quotas, and retention policies will govern the data.
- Leaking private memory or private repo context into public answers because it "helps" the assistant sound useful.
- Treating synthetic datasets as automatically harmless; synthetic prompts can still reveal business logic, security posture, or operational abuse patterns.
- Promising reproducible runs without pinning model/judge versions or admitting that hosted models may not reproduce token-for-token.
- Writing "we will evaluate quality" without defining quality.

### Stretch goals

- Add a lightweight Mermaid or SVG architecture diagram.
- Add a `make safety-scan` command.
- Add a one-page candidate-agent product contract that a recruiter can skim.

---

## Week 2 — Candidate-Agent Dataset Contracts and Schema Validators

### Objective

Build synthetic recruiter-evidence datasets, citation contracts, evidence-strength labels, and validators for the `ryanprasad.ai` candidate evidence chatbot before running eval jobs.

### Why it matters

AWS eval jobs are schema-sensitive, and public evidence bots are claim-sensitive. A harness engineer should fail bad data, unsafe examples, bad citations, inflated evidence strength, and private identifiers locally, not after a cloud job burns time and money or a public bot emits recruiter fan fiction.

### AWS services/docs to study

- Bedrock model evaluation prompt datasets for model-as-judge
- Bedrock custom metrics job docs
- Bedrock RAG retrieve-and-generate prompt dataset docs
- AgentCore input spans/events and dataset evaluation docs

### Build tasks

1. Create JSON Schemas for:
   - model evaluation prompt datasets;
   - model BYOI responses;
   - RAG retrieve-and-generate BYOI datasets;
   - retrieval-only RAG BYOI datasets;
   - candidate-agent chat-turn examples;
   - citation arrays and source-label constraints;
   - evidence-strength labels;
   - refusal/escalation outcomes;
   - run manifests.
2. Build `scripts/validate_dataset.py`:
   - accepts `--schema` and `--input`;
   - validates JSONL line-by-line;
   - reports line numbers and failure reasons;
   - refuses files with obvious secrets, real emails, Slack/channel IDs, account IDs, private hostnames, local paths, raw traces, or private identifiers.
3. Create tiny synthetic datasets under `datasets/synthetic/`:
   - recruiter/project questions about public GitHub-style project summaries, using synthetic public-safe source snippets;
   - unsupported/private-info questions where the right answer is refusal or "I don't know";
   - prompt-injection attempts using inert canaries such as `INJECTION_CANARY_DO_NOT_FOLLOW`, not working attack text;
   - spam/rate-limit cases across chat;
   - 10 intentionally invalid examples under a test fixture directory.
4. Write `docs/dataset-contracts.md` explaining what each schema is for and which evaluation lane consumes it.
5. Give every schema a `schema_version` field and keep golden valid/invalid fixtures under a test directory, so CI can prove a schema change did not silently break old data.

### Validation checks

- Valid datasets pass locally.
- Invalid fixtures fail locally with clear messages.
- JSONL remains line-delimited, not a giant JSON array.
- Dataset examples use only synthetic or explicitly public-safe content.
- Citation/evidence schemas reject nonexistent source labels, missing citations for material claims, and unsupported evidence-strength upgrades.
- Prompt-injection examples are inert canary cases, not working payloads.
- Schemas carry a version, and golden fixtures pin expected pass/fail outcomes.

### Public-safe artifacts to commit

- `schemas/*.schema.json`
- `datasets/synthetic/*.jsonl`
- `scripts/validate_dataset.py`
- `docs/dataset-contracts.md`

### Common failure modes

- Mixing model evaluation, RAG evaluation, and agent/tool schemas.
- Letting the RAG dataset become generic instead of reflecting the chatbot's public project Q&A job.
- Assuming Bedrock model-eval BYOI means live arbitrary inference. It means you provide `modelResponses` in AWS's expected dataset shape; live app evaluation belongs in AgentCore online/on-demand/batch/dataset evaluation where supported, or in a custom trace/output capture pipeline.
- Forgetting Bedrock model BYOI constraints (e.g. one model response per prompt and one unique model identifier per job — confirm the current rules in the linked docs).
- Ignoring Bedrock-native comparison/reporting workflows and building external fan-out for comparisons the managed service already supports.
- Changing a schema without bumping its version or updating fixtures, so old datasets break silently. For any non-synthetic data later, record license/provenance; this repo stays synthetic-only unless the source is explicitly curated as public-safe.

### Stretch goals

- Add unit tests for validators.
- Add a schema compatibility matrix for Bedrock model eval, RAG eval, AgentCore, and Inspect AI.
- Add a contract test that blocks unsupported skill claims without citations.

---

## Week 3 — Production Trace Capture and Observability Baseline

### Objective

Instrument the `ryanprasad.ai` candidate evidence chatbot so Bedrock invocation logs, chat turns, source labels, evidence-strength labels, refusals, latency, token/cost usage, and errors produce structured evidence. Export traces in OpenTelemetry/OpenInference-compatible form where applicable.

### Why it matters

You cannot debug what you did not capture. Eval quality depends on trace quality. For this lab, Bedrock invocation logging is valuable because it captures the actual model request/response bodies and metadata. It still does not replace app traces: invocation logs do not know expected citations, evidence-strength labels, scorer results, source allowlists, deployment versions, or pass/fail status. The public repo gets schemas, examples, and normalized reports — raw invocation logs stay in lab S3.

### AWS services/docs to study

- Bedrock model invocation logging
- AgentCore Observability and input spans/events
- OpenTelemetry/OpenInference instrumentation concepts
- CloudWatch Logs and Logs Insights
- S3 object layout patterns
- CloudTrail audit events

### Build tasks

1. Enable Bedrock invocation logging for lab/eval runs to same-Region S3, using a placeholder bucket layout:
   - `s3://example-eval-bucket/bedrock-invocation-logs/`;
   - `s3://example-eval-bucket/eval-runs/<run_id>/raw/`;
   - `s3://example-eval-bucket/eval-runs/<run_id>/normalized/`;
   - `s3://example-eval-bucket/eval-runs/<run_id>/reports/`.
2. Define trace events for the candidate agent:
   - chat turn received;
   - intent classification;
   - source query/context, source labels, citations, evidence-strength label, and final answer;
   - unsupported/private-info refusal and escalation;
   - latency, token/cost estimate, rate-limit decision, and error fields.
3. Emit normalized JSON trace exports with:
   - run/session ID;
   - prompt or invocation-log reference for lab artifacts;
   - synthetic input in public examples;
   - candidate agent version;
   - model/provider ID;
   - generated answer;
   - reference answer where applicable;
   - public source citations;
   - source labels or passage IDs;
   - evidence-strength label;
   - citation list;
   - latency;
   - token/cost estimate placeholders;
   - error fields.
4. For agent-shaped examples, preserve OpenTelemetry/OpenInference-compatible identifiers and span/event fields:
   - session ID;
   - trace ID;
   - span ID;
   - scope/name/kind where relevant;
   - model invocation spans;
   - retrieval/source-selection spans;
   - citation/evidence-label events;
   - refusal/escalation events;
   - CloudWatch log group and retention placeholders.
5. Write `docs/observability.md`:
   - Bedrock invocation logging is enabled for lab/eval runs;
   - raw invocation logs are useful eval artifacts, not public report material;
   - same-Region S3 destination, run-prefix layout, lifecycle expiration, and access boundaries;
   - how the logging destination inherits prompt/response sensitivity (KMS-encrypt it, lock IAM, bound retention, keep it out of public artifact pipelines);
   - CloudWatch/S3/Athena query plan;
   - how normalized trace exports and invocation-log-derived BYOI datasets feed Bedrock/RAG/AgentCore/Inspect eval lanes.
6. Add sample CloudWatch Logs Insights and Athena queries as documentation, using placeholders only.

### Validation checks

- Traces validate against your schema.
- A failed candidate call produces a structured error record.
- Public examples do not contain raw invocation logs, visitor content, live identifiers, or sensitive data.
- Evidence traces show source labels, citations, and evidence-strength labels.
- RAG/app traces contain citations for supported answers and refusal/"I don't know" outcomes for unsupported questions.
- Bedrock invocation logs can be correlated to app-level eval records by run ID or request metadata.
- Agent traces keep OpenTelemetry/OpenInference compatibility; local JSON schemas describe sanitized exports, not a replacement telemetry standard.
- You can answer: "What failed, how often, and where is the evidence?"

### Public-safe artifacts to commit

- `src/trace_writer.py` or equivalent
- `schemas/trace-export.schema.json`
- `docs/observability.md`
- `docs/queries.md`

### Common failure modes

- Logging everything forever without S3 lifecycle expiration and a lab-artifact policy.
- Committing raw production traces because they are "just examples."
- Assuming model invocation logging replaces app-level eval traces or covers every possible Bedrock endpoint.
- Designing a custom agent trace schema first and then trying to map it back to AgentCore after the fact.
- Treating the invocation-logging destination as plumbing when it actually holds full prompts and responses — a sensitive store that needs the same controls as the data itself.
- Failing to record inference parameters, making reruns non-reproducible.

### Stretch goals

- Add OpenTelemetry trace IDs to local traces.
- Generate a tiny static HTML report from sample traces.
- Add a sanitized production-trace summary format with no raw visitor content.

---

## Week 4 — Bedrock Model Evaluations: Managed Judge Jobs

### Objective

Prepare and run the model evaluation lane using Bedrock Evaluations for candidate-agent responses that are not primarily retrieval or tool-trajectory checks.

### Why it matters

Managed eval jobs are useful, but only when you understand their schemas, job boundaries, and reporting model. The durable, committable artifact this week is a *validated adapter output + a placeholder job template + a runbook* — running a live job is optional, belongs in a sandbox account, and its outputs stay out of this repo (see Managed Job Boundaries).

### AWS services/docs to study

- Bedrock model evaluation jobs
- Model-as-judge prompt datasets
- Built-in metrics and custom metrics
- S3 input/output configuration
- IAM permissions for Bedrock eval jobs

### Build tasks

1. Create a model evaluation dataset adapter:
   - from normalized candidate-agent trace exports and lab Bedrock invocation logs;
   - to Bedrock model evaluation JSONL.
2. Create a BYOI model evaluation adapter:
   - one model response per prompt;
   - one model identifier per job;
   - evidence that Bedrock skips model invocation for supplied `modelResponses`;
   - support for importing captured chatbot answers from Bedrock invocation logs and app traces as BYOI responses;
   - a native Bedrock comparison/reporting plan first, with separate manifests only where the selected API/BYOI path requires separate jobs.
3. Write a Bedrock model eval job template:
   - dataset S3 URI placeholder;
   - output S3 URI placeholder;
   - evaluator model placeholder;
   - built-in metric selection;
   - custom metric references.
4. Add `docs/week-04-model-evals-runbook.md` with CLI/SDK pseudocode and expected outputs.

### Validation checks

- Adapter output validates locally.
- Job templates contain placeholders, not real account details.
- Candidate-agent examples are scoped to supported intents; raw captured outputs stay in lab S3 and normalized/public examples are safe to commit.
- Multi-model or multi-config comparison starts with Bedrock-native reports/comparison where supported; any extra manifests explain why custom coordination is needed.
- Output handling expects managed reports and S3 result artifacts, not console screenshots.

### Public-safe artifacts to commit

- `src/adapters/bedrock_model_eval.py`
- `infra/templates/bedrock-model-eval-job.json`
- `docs/week-04-model-evals-runbook.md`

### Common failure modes

- Overclaiming that Bedrock model eval jobs are a universal benchmark runner.
- Ignoring prompt count limits.
- Forgetting that judge models and rubrics are versioned dependencies.
- Forgetting that evaluator-model and metric availability vary by region, and that every job bills real tokens — bound dataset size, check quotas, and estimate cost before submission.

### Stretch goals

- Build a local summarizer that compares two completed job result folders.
- Add confidence interval calculations for repeated runs.

---

## Week 5 — Custom Metrics and Judge Rubric Engineering

### Objective

Design, validate, and version custom LLM-as-judge metrics.

### Why it matters

A judge prompt is production logic. Treat it like code, not a magic incantation.

### AWS services/docs to study

- Bedrock custom metric creation
- Custom metric rating scales and output schemas
- Human evaluation workflows

### Build tasks

1. Create a rubric library under `rubrics/`:
   - correctness;
   - harmlessness;
   - instruction following;
   - citation support;
   - refusal appropriateness;
   - citation support;
   - evidence-strength calibration.
2. For each rubric, define:
   - purpose;
   - allowed scores;
   - judge instructions;
   - output schema;
   - examples of good/bad judgments.
3. Build a calibration dataset:
   - 50 synthetic examples;
   - examples from public project Q&A, citation support, evidence-strength calibration, unsupported/private-info, and inert injection classes;
   - human labels;
   - expected failure labels.
4. Write a judge validation notebook or script:
   - judge-vs-human agreement;
   - inter-rater agreement beyond raw accuracy (e.g. Cohen's kappa), so chance agreement does not flatter the judge;
   - confusion matrix;
   - false positives/false negatives;
   - mandatory repeated-run variance analysis, because LLM judges can vary across runs even when inputs and parameters are pinned;
   - bias probes for position and verbosity effects, plus self-preference when the judge shares a model family with the candidate.

### Validation checks

- Each rubric has a version and owner.
- Judge outputs are machine-parseable.
- Human labels are stored separately from generated model outputs.
- You can identify which labels the judge gets wrong.
- Repeated-run variance is measured and reported before any judge score is used as a regression gate.
- No judge gates anything until it clears a documented agreement bar against human labels.

### Public-safe artifacts to commit

- `rubrics/*.md`
- `schemas/judge-output.schema.json`
- `datasets/synthetic/human-labels.jsonl`
- `scripts/judge_calibration_report.py`
- `docs/judge-validation.md`

### Common failure modes

- Treating judge scores as truth instead of measurements with error bars.
- Reporting raw agreement while ignoring chance agreement, repeated-run variance, judge drift across evaluator-model versions, and position/verbosity bias.
- Writing vague rubrics that produce pretty prose but no usable score.
- Forgetting that AWS custom metrics may not visualize as expected without output schema/rating scale structure.
- Building the harmlessness/refusal calibration set out of genuinely operational harmful prompts — synthetic is not the same as safe. Keep committed examples non-operational (category labels, not working instructions); see Working Assumptions.

### Stretch goals

- Compare two evaluator models.
- Add bootstrap confidence intervals.

---

## Week 6 — Bedrock RAG Evaluations: Retrieval and Retrieve-and-Generate

### Objective

Build the RAG evaluation lane for the candidate agent's GitHub/project Q&A, with both retrieval-only and end-to-end retrieve-and-generate datasets, while preserving RAG source/configuration identity for native comparison and managed reports.

### Why it matters

RAG failures split into retrieval failures and generation failures. If you only score the final answer, you will blame the wrong subsystem. For a public portfolio chatbot, the invariant is simple: answers about Ryan's projects must be grounded in public/project-safe sources or say "I don't know."

### AWS services/docs to study

- Bedrock Knowledge Base evaluation
- Retrieval-only custom RAG evaluation
- Retrieve-and-generate custom RAG evaluation
- RAG evaluation reports and supported comparison workflows
- RAG metrics: context relevance, context coverage, correctness, completeness, faithfulness, harmfulness, answer refusal, citation precision, citation coverage (treat this list as illustrative — confirm the metric names and availability currently offered in the linked RAG evaluation docs)

### Build tasks

1. Create a public/project-safe RAG corpus plan:
   - public GitHub README/project summaries;
   - public-safe curated project notes;
   - source URL/title placeholders where needed;
   - explicit exclusion of private repos, private memory, Honcho/Graphiti content, private transcripts, raw issue exports, private paths, and generated provider responses.
2. Create synthetic RAG corpus and questions that mirror the candidate agent:
   - recruiter-style project questions;
   - technical architecture questions;
   - "what did Ryan build?" summaries;
   - unsupported/private-info questions where the correct outcome is "I don't know" or refusal;
   - distractor passages and stale-source cases.
3. Build adapters for:
   - retrieval-only BYOI;
   - retrieve-and-generate BYOI;
   - normalized candidate-agent trace exports and lab invocation logs to Bedrock RAG JSONL.
4. Define a RAG source/configuration registry:
   - Bedrock Knowledge Base ID placeholder;
   - external RAG source ID placeholder;
   - retriever/generator configuration ID;
   - index/corpus version;
   - public-source provenance and citation format;
   - native Bedrock report/comparison mapping where supported;
   - separate job manifest mapping where the selected custom BYOI path is scoped to one RAG source.
5. Add a retrieval diagnostic report:
   - top-k retrieved passages;
   - expected supporting passage;
   - missing-context failures;
   - irrelevant-context failures.
6. Write `docs/rag-eval-runbook.md`.

### Validation checks

- Retrieval-only metrics can be interpreted separately from answer metrics.
- RAG reports clearly identify each source/configuration; native comparison/reporting is used where supported.
- If the chosen custom BYOI path is scoped to one RAG source, the runbook documents that as a path-specific constraint instead of a blanket RAG architecture rule.
- References and retrieved passages are synthetic or explicitly public-safe.
- Supported project answers cite public sources.
- Unsupported project/private-info questions produce "I don't know" or refusal, not invented detail.
- Citation metrics are only used when citation structures exist.

### Public-safe artifacts to commit

- `datasets/synthetic/rag-corpus.md` or JSONL equivalent
- `src/adapters/bedrock_rag_eval.py`
- `scripts/rag_diagnostics.py`
- `docs/rag-eval-runbook.md`

### Common failure modes

- Collapsing retrieval quality and generation quality into one vague score.
- Treating "Ryan probably knows this" as support. The check is whether the public corpus supports it.
- Missing the required RAG-source identifier in custom RAG BYOI output (confirm the exact field name, e.g. `knowledgeBaseIdentifier`, in the linked dataset docs).
- Losing RAG source/config IDs, which makes native reports and any cross-job comparison impossible to interpret.
- Treating a custom BYOI one-source constraint as if all Bedrock RAG comparison paths had the same shape.

### Stretch goals

- Add an adversarial RAG set with distractor documents.
- Add a “retrieval changed but answer did not” analysis.

---

## Week 7 — Deterministic Scorers and Small Event Glue

### Objective

Build deterministic scorers that complement LLM judges, with Lambda limited to tiny code-based evaluators or event glue.

### Why it matters

LLM judges are flexible. Deterministic scorers are boring in the best possible way. You want both.

### AWS services/docs to study

- Lambda for lightweight validation and dispatch
- AgentCore code-based evaluator Lambda contract
- Step Functions task states
- S3 event-driven workflows
- CloudWatch metrics

### Build tasks

1. Implement scorers for:
   - exact match;
   - JSON schema validity;
   - required field presence;
   - refusal phrase detection;
   - citation format validity;
   - citation source allowlist/no-private-source checks;
   - no-secret/no-private-identifier checks;
   - citation presence and source-label validity;
   - evidence-strength label validity;
   - no unsupported production-claim upgrades.
2. Package scorers as local CLI functions first.
3. Design optional Lambda wrappers only for tiny deterministic checks, AgentCore code-based evaluators, or event dispatch glue.
4. Define when **not** to use Lambda:
   - long-running evals;
   - large batch processing;
   - heavy model/tool simulations;
   - complex Inspect AI tasks.
5. Route sustained evaluation work to managed Bedrock/AgentCore jobs, SageMaker, ECS, or AWS Batch.

### Validation checks

- Scorers are deterministic and unit-tested.
- Scorer outputs include version, inputs, score, and explanation.
- Citation and evidence-calibration scorer failures can block a candidate-chatbot release before recruiter-facing answers ship.
- Lambda design is explicitly optional and small; sustained eval runtime is assigned to managed Bedrock/AgentCore jobs, SageMaker, ECS, or AWS Batch.

### Public-safe artifacts to commit

- `src/scorers/*.py`
- `tests/test_scorers.py`
- `docs/scorer-library.md`
- `infra/templates/lambda-scorer-wrapper.md` if you include tiny Lambda evaluators/glue

### Common failure modes

- Using LLM-as-judge for things a regex/schema can catch perfectly.
- Putting heavyweight eval runners in Lambda because “serverless” sounds tidy.
- Failing to version scorers.

### Stretch goals

- Add scorer result aggregation.
- Emit CloudWatch Embedded Metric Format examples with synthetic values.

---

## Week 8 — AgentCore Evaluations for Agents and Tool Use

### Objective

Keep AgentCore/tool evaluation as an explicit Phase 2 lane. V1 should first prove the citation-backed recruiter-evidence chatbot; if Calendar or Slack tools return later, evaluate those tool trajectories in the same pipeline.

### Why it matters

Agent eval is not just "did the final answer sound okay?" You need traces: tool choice, arguments, order, confirmation state, recovery behavior, safety boundaries, and state transitions. AgentCore Evaluations is not a separate island; it plugs into the same manifest, security, quota, reporting, and regression-gate pipeline as the model and RAG lanes. The durable, checkable artifact this week is OpenTelemetry/OpenInference-compatible synthetic traces, evaluator specs, and a runbook. A live managed agent eval is useful, but not required for a public-safe learning artifact.

### AWS services/docs to study

- Bedrock AgentCore Evaluations
- AgentCore online, on-demand, batch, and dataset evaluation modes
- OpenTelemetry and OpenInference trace/span/event concepts
- AgentCore Observability and CloudWatch Transaction Search
- Strands and LangGraph integration patterns
- Evaluation modes and framework integrations as currently documented — AgentCore Evaluations is newer and evolving, so confirm exact mode names, supported integrations, and trace formats in the linked doc rather than trusting this list

### Build tasks

1. Define an agent task suite:
   - project Q&A should use public evidence, not tool actions;
   - unsupported evidence should refuse or say "I don't know";
   - citation support should be present for material claims;
   - wrong-action detection if a future tool is added;
   - tool argument validity only for Phase 2 synthetic tools;
   - multi-turn state tracking;
   - safe refusal;
   - recovery from tool failure;
   - prompt-injection resistance using inert canaries.
2. Create synthetic OpenTelemetry/OpenInference-compatible trace examples.
3. Build an adapter from internal normalized exports to AgentCore-compatible spans/events without making the custom export schema the primary trace model.
4. Define custom agent evaluators:
   - wrong action;
   - unsafe tool call;
   - missing confirmation for any future write action;
   - hallucinated external action;
   - failed recovery.
5. Show how the same run manifest records AgentCore evaluator IDs, evaluation mode, CloudWatch log group placeholders, KMS/retention decisions, and token usage.
6. Write `docs/agentcore-evals-runbook.md`.

### Validation checks

- Agent tasks inspect trace behavior, not only final text.
- Tool-call arguments are checked deterministically where possible.
- Tool choice is correct for RAG answer, refusal, unsupported intents, and any optional Phase 2 tool flows.
- Optional tool trajectories prove consent, valid arguments, and rate-limit handling before any future write feature ships.
- Safety evals distinguish “refused safely” from “failed to complete.”
- AgentCore outputs join the same run-result/reporting path as Bedrock model and RAG evaluations.
- Simulation mode is treated as useful but not equivalent to production behavior.
- Synthetic traces remain OpenTelemetry/OpenInference-compatible and validate against `schemas/agent-trace-export.schema.json` as a public-safe export contract.

### Public-safe artifacts to commit

- `agentcore/trace-examples/*.json`
- `agentcore/evaluators/*.md`
- `src/adapters/agent_trace_adapter.py`
- `docs/agentcore-evals-runbook.md`

### Common failure modes

- Treating agents as chatbots with extra steps.
- Ignoring tool arguments and side effects.
- Treating AgentCore as a separate reporting island instead of feeding its results back into the shared manifest and evidence model.
- Committing real agent traces — tool inputs/outputs and intermediate state routinely carry sensitive data; keep repo traces synthetic/public-safe and raw lab traces in S3.
- Committing working prompt-injection or jailbreak payloads. The resistance suite describes attacks; keep the committed version inert (attack class plus a canary string), not a copy-pasteable exploit. See Working Assumptions.
- Calling simulated success “production ready.”

### Stretch goals

- Add a tiny Strands or LangGraph demo agent with synthetic tools.
- Add a replay harness for saved traces.

---

## Week 9 — Inspect AI on AWS for Programmatic Evals

### Objective

Run advanced/custom evals with Inspect AI on AWS infrastructure.

### Why it matters

Some evals are programs: multi-step tasks, tool-use games, sandboxed code checks, adversarial policies, and custom scoring logic. Managed judge jobs are not enough.

### AWS services/docs to study

- SageMaker Inspect AI container docs
- SageMaker Training Jobs
- Bedrock model provider usage from Inspect
- S3 benchmark/result storage
- ECS or AWS Batch as alternative execution backends

### Build tasks

1. Write one Inspect AI task for:
   - model-only response quality for candidate-agent turns;
   - RAG answer checking for public GitHub/project Q&A;
   - optional Phase 2 agent/tool-use replay from synthetic/public-safe traces.
2. Create an Inspect recipe YAML with:
   - model configuration placeholder;
   - dataset path placeholder;
   - concurrency;
   - retries;
   - timeout;
   - output S3 path placeholder.
3. Document SageMaker execution role permissions at a high level.
4. Add a local dry-run path for small synthetic tasks.

### Validation checks

- Inspect tasks can run locally against synthetic data.
- AWS recipe uses placeholders only.
- Output format can be summarized into the same run manifest/reporting system.
- Heavy eval workloads are not routed through Lambda.

### Public-safe artifacts to commit

- `inspect/tasks/*.py`
- `inspect/recipes/*.yaml`
- `docs/inspect-ai-on-aws.md`
- `src/adapters/inspect_results_adapter.py`

### Common failure modes

- Treating Inspect AI as interchangeable with Bedrock Evaluations.
- Forgetting IAM/S3 permissions for SageMaker jobs.
- Losing result provenance when importing Inspect outputs.
- Forgetting that Inspect still calls a real model provider — runs cost tokens and send your eval data to that provider; record the provider, model version, and run cost in the manifest.

### Stretch goals

- Add an ECS/Batch design alternative.
- Build a task that compares two candidate systems through separate run manifests.

---

## Week 10 — Orchestration, Manifests, and Repeatable Evidence

### Objective

Build the orchestration layer that turns candidate-agent traces, datasets, and eval pieces into repeatable runs.

### Why it matters

A harness is the system that runs deterministic preflight and data-processing steps the same way twice, records non-deterministic model/judge dependencies honestly, explains what changed, and leaves evidence behind.

### AWS services/docs to study

- Step Functions
- EventBridge
- S3 object versioning
- Glue/Athena
- CodeBuild for CI-style execution

### Build tasks

1. Design a Step Functions workflow:
   - verify Region, IAM, KMS, S3, CloudWatch retention, model access, and quotas;
   - estimate cost before job submission;
   - validate dataset;
   - generate synthetic candidate responses or import normalized lab trace exports;
   - dispatch Bedrock model eval jobs;
   - dispatch RAG eval jobs for public project Q&A;
   - dispatch optional AgentCore evals for Phase 2 tool trajectories and refusal paths;
   - dispatch Inspect/custom tasks;
   - aggregate results;
   - publish report.
2. Implement local workflow simulation:
   - use synthetic data;
   - create run manifest;
   - write result summary.
3. Create `schemas/run-result.schema.json`.
4. Write `docs/orchestration.md`.

### Validation checks

- Each run has a stable run ID and manifest.
- Results can be traced back to dataset, code, prompt, model, scorer, and judge versions.
- Deterministic components reproduce exactly; hosted model and LLM-judge outputs are compared statistically across repeated runs instead of promised token-for-token.
- Failures are captured as structured states, not lost terminal output.
- Managed-job IDs are persisted in the manifest so result artifacts can be fetched and re-summarized later.
- A retried run is idempotent or resumable: it reuses its run ID and does not silently double-bill managed jobs.
- Lab-derived runs use normalized exports for public artifacts and keep raw invocation logs/traces in S3.

### Public-safe artifacts to commit

- `infra/step-functions/eval-harness.asl.json`
- `src/manifests/*.py`
- `scripts/run_local_harness.py`
- `docs/orchestration.md`

### Common failure modes

- Creating one giant script with no job boundaries.
- Failing to distinguish candidate generation from scoring.
- Storing reports without the manifest needed to reproduce them.
- Losing managed-job IDs, so you cannot fetch the result artifacts you already paid for.
- Using Step Functions to rebuild comparison/reporting that Bedrock already provides for the selected evaluation path.

### Stretch goals

- Add a static report generator.
- Add Athena table definitions for S3 result layout.

---

## Week 11 — CI/CD, Regression Gates, Monitoring, and Cost Controls

### Objective

Turn the harness into a system that can block bad changes and explain cost/performance drift.

### Why it matters

Evals become real when they affect shipping decisions. Otherwise they are a dashboard-shaped screensaver.

### AWS services/docs to study

- CodeBuild/CodePipeline or GitHub Actions with AWS OIDC
- CloudWatch metrics and alarms
- Service Quotas, AWS Budgets, Cost Explorer, and cost allocation tags
- IAM least privilege and KMS encryption

### Build tasks

1. Add local CI checks:
   - dataset validation;
   - unit tests;
   - public-safety scan;
   - markdown/link checks if available.
2. Define regression gates:
   - deterministic scorer thresholds;
   - judge score thresholds backed by calibration and repeated-run variance;
   - citation/no-private-source gates for public project answers;
   - citation support, source-label validity, and evidence-strength calibration gates;
   - allowed confidence interval movement;
   - cost/latency budgets.
3. Design AWS CI/CD path:
   - CodeBuild or GitHub Actions OIDC;
   - deploy/update eval infrastructure;
   - trigger scheduled synthetic eval runs and normalized lab-trace eval runs;
   - publish summary report.
4. Write `docs/regression-gates.md` and `docs/cost-controls.md`.

### Validation checks

- CI fails on invalid datasets.
- CI fails on unsafe public examples.
- Regression gates are documented with rationale.
- Cost controls separate experiment budget from any production monitoring path.
- Monitoring tracks refusal rate, unsupported-question rate, citation failures, evidence-strength calibration failures, rate-limit decisions, latency, token usage, and cost; raw model I/O remains in lab S3 invocation logs.
- Every run records a per-run cost estimate, Service Quotas checks, maximum prompt count, maximum candidate/config count, maximum repeated-run count, and required approval state before submitting managed jobs.
- Tags are included for allocation, but they are not the control plane; quotas, budgets, pre-submit estimates, and hard manifest limits stop runaway jobs.
- Committed IAM/KMS templates use scoped, per-lane roles and customer-managed KMS key placeholders, with wildcard (`*`) exceptions documented and justified if AWS requires them.

### Public-safe artifacts to commit

- `.github/workflows/validate.yml` or equivalent placeholder workflow
- `docs/regression-gates.md`
- `docs/cost-controls.md`
- `scripts/check_regression_gate.py`

### Common failure modes

- Setting arbitrary thresholds without calibration.
- Letting eval cost grow invisibly because tags exist but no quota, estimate, budget, or max-run guardrail blocks submission.
- Shipping IAM policies with wildcard actions/resources because least privilege is annoying.
- Treating CloudWatch alarms as quality evals instead of operational signals.

### Stretch goals

- Add a small synthetic “before/after” report showing a regression caught by CI.
- Add cost-per-eval-run estimates.

---

## Week 12 — Capstone: AWS Eval Harness Reference Architecture

### Objective

Package the whole thing into a deployable, reviewable, public-safe reference architecture and final evidence packet for the `ryanprasad.ai` candidate agent.

### Why it matters

This is the artifact that says: “I do not merely know eval words. I can build the machine.”

### AWS services/docs to study

Review everything from Weeks 1-11, then focus on integration gaps.

### Build tasks

1. Assemble the capstone package:
   - candidate-agent product/eval contract;
   - CDK or Terraform stack skeleton;
   - S3 bucket layout;
   - IAM/KMS policy placeholders;
   - Step Functions workflow;
   - optional tiny Lambda scorer/evaluator wrappers or event glue;
   - SageMaker/ECS/Batch custom eval runner option;
   - Bedrock model eval job templates;
   - Bedrock RAG eval job templates;
   - AgentCore evaluator config/examples;
   - Inspect AI recipe/task;
   - schemas and validators;
   - run manifest and result summarizer;
   - dashboards/runbooks;
   - public-safe report for GitHub/project answers, citations, evidence-strength calibration, refusals, latency, and cost.
2. Run an end-to-end synthetic local harness run.
3. If using an AWS sandbox account, run one minimal live cloud path and keep live output out of the repo.
4. Publish a final report under `docs/reports/capstone.md` with:
   - what was built;
   - what was validated;
   - what was not validated;
   - what live-chatbot evidence was synthetic vs lab-derived;
   - cost/security assumptions;
   - known limitations;
   - next steps.

### Validation checks

- A reviewer can clone the repo and understand the architecture without private context.
- Local synthetic validation passes.
- Cloud instructions use placeholders only.
- Claims match evidence.
- The public evidence packet can be read without private context and contains no raw invocation logs, raw traces, emails, Slack IDs, calendar IDs, account IDs, private URLs, or secrets.
- The public report does not imply production readiness, safety certification, universal correctness, or magic eval truth.

### Public-safe artifacts to commit

- `docs/reports/capstone.md`
- `docs/runbook.md`
- `infra/README.md`
- `src/README.md`
- final schemas, adapters, validators, scorers, templates, and reports

### Common failure modes

- Publishing cloud screenshots or logs with identifiers.
- Saying “production-ready” when only synthetic local tests ran.
- Publishing raw chatbot traces or tool outputs as evidence.
- Letting the capstone become a pile of disconnected files instead of a harness.
- Claiming the reference architecture proves more than its scenario-specific evidence supports.

### Stretch goals

- Add a short demo video or GIF using only synthetic data.
- Add a one-command local demo.
- Add a “teach this as a workshop” facilitator guide.

---

## Capstone Package Checklist

The finished package should include:

- **Infrastructure**
  - CDK or Terraform skeleton;
  - S3 bucket layout;
  - KMS encryption placeholders;
  - IAM least-privilege role templates;
  - Step Functions workflow definition;
  - optional EventBridge schedule;
  - optional CodeBuild/GitHub Actions integration.
- **Dataset layer**
  - synthetic model eval dataset;
  - synthetic public GitHub/project Q&A RAG dataset;
  - citation-support and evidence-strength datasets;
  - unsupported/private-info, inert prompt-injection, and spam/rate-limit datasets;
  - human-label calibration set;
  - dataset schemas and validators.
- **Adapter layer**
  - internal trace to Bedrock model eval;
  - internal trace to Bedrock RAG eval;
  - normalized trace export to AgentCore-compatible OpenTelemetry/OpenInference spans/events;
  - Inspect result adapter;
  - run manifest writer.
- **Scoring layer**
  - deterministic scorer library;
  - citation/no-private-source/no-secret checks;
  - citation support and source-label validity checks;
  - evidence-strength calibration checks;
  - custom metric/rubric library;
  - judge validation report;
  - regression gate checker.
- **Execution layer**
  - Bedrock model eval job templates;
  - Bedrock RAG eval job templates;
  - AgentCore evaluator examples;
  - Inspect AI task and recipe;
  - local harness simulator.
- **Ops layer**
  - CloudWatch metric examples;
  - Athena/Glue query examples;
  - lab invocation-log capture, normalization, and lifecycle notes;
  - quota checks, budgets, pre-submit cost estimates, and cost allocation tags;
  - CloudTrail/audit notes;
  - runbook.
- **Evidence layer**
  - public-safe candidate-agent evidence packet;
  - synthetic run summary;
  - normalized lab-derived summary if used;
  - limitations section;
  - source ledger.

## Decision Matrix

| Need | Prefer | Why |
| --- | --- | --- |
| Judge model answers against a rubric | Bedrock Model Evaluation | Managed scoring, built-in/custom metrics, S3-backed jobs |
| Score BYOI model responses | Bedrock Model Evaluation BYOI | Useful when candidate outputs are generated outside Bedrock |
| Score retrieval quality | Bedrock RAG retrieval evaluation | Separates retrieval from generation failures |
| Score RAG answer quality | Bedrock RAG retrieve-and-generate evaluation | Uses RAG-specific metrics such as faithfulness and citation coverage |
| Evaluate public project Q&A | Bedrock RAG evals + deterministic citation/source checks | Verifies the chatbot answers from public/project-safe support or says "I don't know" |
| Evaluate live or captured agent behavior | Bedrock AgentCore online/on-demand/batch/dataset evaluations | Designed around sessions, traces, spans, tool calls, and evaluator modes |
| Evaluate future Calendar/Slack tool flows | AgentCore evals + deterministic schema/consent/rate-limit scorers | Phase 2 only; tool choice and side effects need trace-level evidence, not just final-answer grading |
| Run complex programmatic evals | Inspect AI on SageMaker/ECS/Batch | Eval logic is code, not only judge prompts |
| Validate data and run lightweight scoring | Local CLI first; tiny Lambda only for small code-based evaluators or event glue | Fast schema checks and deterministic scoring without turning Lambda into an eval runtime |
| Coordinate managed and custom work | Bedrock-native workflows first, Step Functions when preflight/CI/CD/cross-service glue is needed | Use managed comparison/reporting where supported; add explicit state, retries, failure handling, and auditability around it |
| Query historical results | S3 + Glue/Athena | Cheap evidence lake pattern |
| Block regressions in development | CI/CD regression gates | Converts evals into shipping discipline |

> The managed Bedrock rows still leave you owning preflight, dataset/trace prep, versioning, validation, judge calibration, and scenario-specific interpretation. Use native reports and comparison first; custom summarization is for unsupported views or cross-lane evidence.

## What Not to Overclaim

Do not claim:

- “Bedrock Evaluations is the whole harness.” It is a managed evaluation component.
- “BYOI evaluates any live app automatically.” Bedrock model-eval BYOI means you provide `modelResponses` in the expected schema and Bedrock skips model invocation; live app evaluation belongs in AgentCore-supported flows or a custom capture pipeline feeding supported inputs.
- “LLM-as-judge is ground truth.” It is a judge with measurable error.
- “Synthetic tests prove production safety.” They prove behavior on synthetic tests.
- “The candidate agent is safe because it has evals.” Evals are scoped evidence, not a guarantee.
- “Agent simulation equals production behavior.” It is useful evidence, not a deployment guarantee.
- “Tool success proves consent.” For any future write action, consent is a recorded state transition before a server-side write, not a pleasant final message.
- “Project Q&A can use anything Ryan has ever written.” Public answers need public/project-safe sources and citations.
- “A passing eval means the model is safe.” It means it passed a scoped test suite.
- “One RAG score explains everything.” Retrieval and generation failures must be separated.
- “Serverless means Lambda for everything.” Heavy eval workloads often belong in SageMaker, ECS, Batch, or managed Bedrock jobs.
- “No private data in repo means no privacy risk.” Cloud logs and S3 outputs can still contain sensitive data.
- “Same prompt, same score.” Hosted models and LLM judges are not guaranteed deterministic even at temperature 0; pin versions, expect drift, measure repeated-run variance, and re-baseline — reproduce the deterministic *harness* components, not the model's every token.
- “A managed eval job verifies correctness.” It applies your dataset and chosen metrics; a model-as-judge still does the scoring, with error.

## Suggested Weekly Rhythm

Use the same loop every week:

1. Read the relevant AWS docs.
2. Add or update schemas.
3. Build a tiny synthetic candidate-agent example.
4. Validate locally.
5. Add a runbook.
6. Add a public-safe report or screenshot-free receipt.
7. Run public-safety scan.
8. Commit only the safe artifacts.

## Source Ledger

Primary AWS references to consult while building this plan:

- Amazon Bedrock Evaluations: <https://aws.amazon.com/bedrock/evaluations/>
- Evaluate Amazon Bedrock resources: <https://docs.aws.amazon.com/bedrock/latest/userguide/evaluation.html>
- Create a model evaluation job using built-in metrics: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-built-in-metrics.html>
- Create a model evaluation job using an LLM as a judge: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-judge-create.html>
- Model evaluation prompt datasets for model-as-judge: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-prompt-datasets-judge.html>
- Model evaluation reports and S3 output layout: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-report.html> and <https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-report-s3.html>
- Custom metrics for model evaluation jobs: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-custom-metrics-create-job.html>
- Bedrock RAG evaluations overview: <https://docs.aws.amazon.com/bedrock/latest/userguide/evaluation-kb.html>
- Create a RAG evaluation job: <https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-evaluation-create.html>
- Knowledge Base retrieve-and-generate prompt datasets: <https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-evaluation-prompt-retrieve-generate.html>
- Custom RAG retrieve-and-generate evaluation: <https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-evaluation-create-randg-custom.html>
- Custom retrieval-only evaluation: <https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-evaluation-create-ro-custom.html>
- RAG evaluation reports and metrics: <https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-evaluation-report.html>
- Bedrock model invocation logging: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html>
- Bedrock model access: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html>
- Bedrock supported models and Regions: <https://docs.aws.amazon.com/bedrock/latest/userguide/models.html>
- Bedrock quotas: <https://docs.aws.amazon.com/bedrock/latest/userguide/quotas.html>
- Bedrock data management and encryption for evaluation jobs: <https://docs.aws.amazon.com/bedrock/latest/userguide/evaluation-data-management.html>
- KMS support in model evaluation jobs: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-security-data.html>
- Data encryption for knowledge base evaluation jobs: <https://docs.aws.amazon.com/bedrock/latest/userguide/rag-evaluation-security-data.html>
- Bedrock AgentCore Evaluations: <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations.html>
- AgentCore evaluation types: <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations-types.html>
- AgentCore online evaluations: <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/online-evaluations.html>
- AgentCore on-demand evaluations: <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-demand-evaluations.html>
- AgentCore batch evaluations: <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/batch-evaluations.html>
- AgentCore dataset evaluations: <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/dataset-evaluations.html>
- AgentCore input spans and events: <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/understanding-input-spans.html>
- AgentCore code-based evaluators: <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-based-evaluators.html>
- AgentCore quotas: <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/bedrock-agentcore-limits.html>
- SageMaker Inspect AI container: <https://docs.aws.amazon.com/nova/latest/userguide/nova-eval-inspect-ai-container.html>

These pages are the source of truth for schemas, field names, metric lists, job constraints, and evaluation modes. This plan paraphrases them to stay readable; where the two disagree, follow the docs, and assume AWS has shipped changes since this was written.

## Final Standard

The final artifact should make one thing obvious: you can build AWS eval infrastructure with disciplined engineering. Not “I prompted a judge model once.” Not “I made a dashboard.” A real learning harness: versioned inputs, scoped claims, repeatable deterministic steps, calibrated judges, measured variance, deterministic checks, traceable outputs, quota-aware cost controls, and public-safe receipts.
