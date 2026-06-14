# AWS AI Evals: 12-Week Hands-On Learning Plan

This is a learning-by-doing path for building an AWS-native and hybrid AI evaluation harness. The goal is not to click around the Bedrock console and declare victory. The goal is to build a small but serious reference architecture: datasets, schemas, validators, managed Bedrock eval jobs, AgentCore agent/tool evals, Inspect AI custom evals, orchestration, observability, cost controls, and public-safe reports.

Bedrock is the judge booth. You still have to build the courthouse.

## North Star

By the end of 12 weeks, you should have a deployable **AWS Eval Harness Reference Architecture** that can:

- evaluate model outputs with Amazon Bedrock Evaluations;
- evaluate RAG retrieval and retrieve-and-generate pipelines;
- evaluate agent/tool behavior with Amazon Bedrock AgentCore Evaluations;
- run programmatic and custom evals with Inspect AI on AWS;
- validate BYOI datasets before jobs run;
- compare judge scores against human labels;
- orchestrate repeatable runs through Step Functions or an equivalent workflow;
- store inputs, outputs, manifests, metrics, reports, and cost traces in S3;
- query results with Athena/Glue or equivalent tooling;
- publish public-safe evidence without leaking prompts, traces, credentials, account details, or private data.

What it is **not**: a universal benchmark runner, a correctness oracle, a safety certificate, or proof of production readiness. The managed Bedrock lanes return S3 artifacts you still have to validate, summarize, and interpret. The harness is the part you own.

## Working Assumptions

Use placeholders and synthetic data throughout:

- AWS account: `111122223333`
- Region: `us-east-1`
- Example bucket: `s3://example-eval-bucket/...`
- Example domain: `example.com`

Do not commit live AWS account IDs, ARNs, bucket names, CloudWatch log output, private traces, local paths, private IPs, Slack IDs, emails, or secrets.

**Synthetic is not the same as safe.** The safety, refusal, and prompt-injection lanes (Weeks 5 and 8) generate *attacks* by design. In a public, billboard-safe repo, keep that content non-operational: name the attack class and use inert canaries (e.g. `INJECTION_CANARY_DO_NOT_FOLLOW`), never working jailbreaks, exploit code, or copy-pasteable harmful instructions. The rules above keep *real* data out; this one keeps *dangerous* content out. An eval repo must not double as an attack cookbook.

### Terms and source of truth

- **BYOI = Bring Your Own Inference responses.** You supply *pre-generated* candidate outputs in AWS's expected dataset shape. It does **not** mean Bedrock runs your live app, calls your endpoints, or orchestrates your stack. You generate the inference; AWS scores what you hand it.
- **The Source Ledger is the source of truth.** This plan paraphrases AWS schemas, field names, metric lists, job constraints, and evaluation modes so you can build against them — but AWS evolves these, and paraphrases drift. Confirm specifics against the linked docs before wiring anything up. When this plan and the docs disagree, the docs win.

## Architecture Lanes

Treat these as separate lanes that converge in the capstone:

1. **Model evaluation lane** — Bedrock model evaluation jobs, model-as-judge, built-in metrics, custom metrics, BYOI model responses.
2. **RAG evaluation lane** — Bedrock Knowledge Base retrieval-only and retrieve-and-generate evaluation, plus custom RAG BYOI datasets.
3. **Agent/tool evaluation lane** — Bedrock AgentCore Evaluations, OpenTelemetry/OpenInference traces, Strands/LangGraph-compatible agent traces, and the evaluation modes the AgentCore docs currently describe (confirm the exact set — this surface is evolving).
4. **Custom harness lane** — Inspect AI, deterministic scorers, schema validators, custom task runners, SageMaker/ECS/Batch execution.
5. **Platform lane** — S3, KMS, IAM, Step Functions, Lambda, CloudWatch, CloudTrail, Athena/Glue, Cost Explorer, CI/CD.

Lanes 1–4 are the **evaluation lanes**; lane 5 is cross-cutting glue. Lanes 1–3 lean on *managed* Bedrock jobs — you own dataset prep, fan-out, and summarization; AWS owns the scoring runtime. Lane 4 is code you run yourself. Keep their datasets, schemas, and result shapes separate; they only converge at the orchestration and reporting layer, and a score from one lane does not transfer to another.

## Managed Job Boundaries (Read Before Week 4)

Bedrock model, RAG, and AgentCore evaluations are *managed jobs*, not a magic verdict service. Before you lean on them, internalize the edges:

- **They run in your account, on your data.** Jobs read inputs from and write outputs to *your* S3, under a service role you scope. Your dataset content flows to the evaluator model. Results come back as S3 artifacts — files you must parse and summarize, not a verdict handed down from the cloud.
- **One job = one scope.** One model (or one RAG source) per job. Multi-system comparisons are *your* fan-out plus *your* summarizer, not one heroic job.
- **The judge is a versioned dependency you do not control.** Evaluator model, rubric, and AWS defaults can change underneath you. Pin and record them; re-baseline when they move.
- **Availability varies — and availability is not access.** Evaluator models, metrics, and eval features are not uniform across regions or models; confirm availability for your region before you design around a feature. Available is also not enabled: whichever models the job invokes (the evaluator always, the candidate unless you brought BYOI responses) must have model access granted in your account, or the job dies at a permissions wall instead of a friendly hint.
- **Quotas and limits are real.** Prompt counts, dataset sizes, and concurrent jobs are bounded — confirm current limits in the docs, not in production at 2am.
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
    agent-trace.schema.json
    run-manifest.schema.json
  datasets/
    synthetic/
      model-prompts.jsonl
      rag-conversations.jsonl
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

## Week 1 — Evaluability Design, Threat Model, and Repo Contracts

### Objective

Define what “evaluatable” means for your target AI application before touching infrastructure.

### Why it matters

Most eval systems fail because the app was never instrumented for evaluation. If prompts, retrieved context, tool calls, errors, and run parameters are not captured consistently, you get vibes in a trench coat instead of evidence.

### AWS services/docs to study

- Amazon Bedrock Evaluations overview
- Bedrock model invocation logging
- CloudWatch Logs, S3, CloudTrail, KMS, IAM basics

### Build tasks

1. Write `docs/evaluability-design-doc.md` with:
   - target app type: model-only, RAG, agent, or hybrid;
   - success criteria;
   - expected failure modes;
   - trace schema draft;
   - privacy/safety policy;
   - cost tagging plan;
   - AWS service responsibility split.
2. Define a run manifest format with fields for:
   - dataset version;
   - prompt version;
   - model/provider ID and pinned model version (an alias can move under you);
   - inference parameters;
   - scorer versions;
   - judge model/rubric versions;
   - random seed where applicable (note that hosted models may ignore it and are not guaranteed deterministic);
   - code commit;
   - AWS region;
   - run timestamp.
3. Draft a public-safe evidence policy:
   - what can be committed;
   - what must stay in S3 only;
   - what must be redacted;
   - how reports are scrubbed.
4. Sketch the architecture in `docs/architecture.md`.
5. Write `schemas/run-manifest.schema.json` and a matching `schemas/examples/run-manifest.example.json` that validates against it — so Week 1 ships a checkable artifact, not just prose.

### Validation checks

- A new contributor can explain what will be evaluated and why.
- Every planned artifact has a safe storage location.
- The design separates model, RAG, agent, and custom harness lanes.
- No live AWS identifiers or private examples are present.
- The example run manifest validates against `schemas/run-manifest.schema.json`.
- Reproducibility is scoped honestly: the manifest pins versions and parameters, but the doc states plainly that hosted models may not reproduce token-for-token.

### Public-safe artifacts to commit

- `docs/evaluability-design-doc.md`
- `docs/architecture.md`
- `schemas/run-manifest.schema.json`
- `schemas/examples/run-manifest.example.json`
- `scripts/public_safety_scan.py`

### Common failure modes

- Treating Bedrock Evaluations as the whole harness.
- Skipping privacy design until after traces contain sensitive data.
- Forgetting that model invocation logging can capture full prompts and outputs, and that its destination then holds that sensitive content.
- Promising reproducible runs without pinning model/judge versions or admitting that hosted models may not reproduce token-for-token.
- Writing “we will evaluate quality” without defining quality.

### Stretch goals

- Add a lightweight Mermaid or SVG architecture diagram.
- Add a `make safety-scan` command.

---

## Week 2 — Dataset Contracts and Schema Validators

### Objective

Build dataset schemas and validators before running eval jobs.

### Why it matters

AWS eval jobs are schema-sensitive. A harness engineer should fail bad data locally, not after a cloud job burns time and money.

### AWS services/docs to study

- Bedrock model evaluation prompt datasets for model-as-judge
- Bedrock custom metrics job docs
- Bedrock RAG retrieve-and-generate prompt dataset docs

### Build tasks

1. Create JSON Schemas for:
   - model evaluation prompt datasets;
   - model BYOI responses;
   - RAG retrieve-and-generate BYOI datasets;
   - retrieval-only RAG BYOI datasets;
   - run manifests.
2. Build `scripts/validate_dataset.py`:
   - accepts `--schema` and `--input`;
   - validates JSONL line-by-line;
   - reports line numbers and failure reasons;
   - refuses files with obvious secrets or private identifiers.
3. Create tiny synthetic datasets under `datasets/synthetic/`:
   - 20 model prompts;
   - 20 RAG questions with synthetic contexts;
   - 10 intentionally invalid examples under a test fixture directory.
4. Write `docs/dataset-contracts.md` explaining what each schema is for.
5. Give every schema a `schema_version` field and keep golden valid/invalid fixtures under a test directory, so CI can prove a schema change did not silently break old data.

### Validation checks

- Valid datasets pass locally.
- Invalid fixtures fail locally with clear messages.
- JSONL remains line-delimited, not a giant JSON array.
- Dataset examples use only synthetic content.
- Schemas carry a version, and golden fixtures pin expected pass/fail outcomes.

### Public-safe artifacts to commit

- `schemas/*.schema.json`
- `datasets/synthetic/*.jsonl`
- `scripts/validate_dataset.py`
- `docs/dataset-contracts.md`

### Common failure modes

- Mixing model evaluation and RAG evaluation schemas.
- Assuming BYOI means live arbitrary inference. It means you provide responses in AWS’s expected dataset shape.
- Forgetting Bedrock model BYOI constraints (e.g. one model response per prompt and one unique model identifier per job — confirm the current rules in the linked docs).
- Trying to compare many models inside one managed job when orchestration should fan out jobs.
- Changing a schema without bumping its version or updating fixtures, so old datasets break silently. For any non-synthetic data later, record license/provenance; this repo stays synthetic-only.

### Stretch goals

- Add unit tests for validators.
- Add a schema compatibility matrix for Bedrock model eval, RAG eval, AgentCore, and Inspect AI.

---

## Week 3 — Trace Capture and Observability Baseline

### Objective

Instrument a small AI app or harness stub so every eval run emits structured traces.

### Why it matters

You cannot debug what you did not capture. Eval quality depends on trace quality.

### AWS services/docs to study

- Bedrock model invocation logging
- CloudWatch Logs and Logs Insights
- S3 object layout patterns
- CloudTrail audit events

### Build tasks

1. Build a minimal local “candidate app” with two modes:
   - model-only Q&A stub;
   - RAG-style answer from synthetic context.
2. Emit JSON traces with:
   - run ID;
   - input prompt;
   - model or candidate ID;
   - generated answer;
   - reference answer where applicable;
   - retrieved passages;
   - tool calls if present;
   - latency;
   - token/cost estimate placeholders;
   - error fields.
3. Write `docs/observability.md`:
   - when to use Bedrock invocation logging;
   - when not to log full prompts/responses;
   - redaction policy;
   - how the logging destination inherits prompt/response sensitivity (KMS-encrypt it, lock IAM, bound retention, keep it out of public artifact pipelines);
   - CloudWatch/S3/Athena query plan.
4. Add sample CloudWatch Logs Insights and Athena queries as documentation.

### Validation checks

- Traces validate against your schema.
- A failed candidate call produces a structured error record.
- Public examples do not contain real prompts or sensitive data.
- You can answer: “What failed, how often, and where is the evidence?”

### Public-safe artifacts to commit

- `src/trace_writer.py` or equivalent
- `schemas/trace.schema.json`
- `docs/observability.md`
- `docs/queries.md`

### Common failure modes

- Logging everything forever without a retention/sensitivity policy.
- Assuming model invocation logging covers every possible Bedrock endpoint.
- Treating the invocation-logging destination as plumbing when it actually holds full prompts and responses — a sensitive store that needs the same controls as the data itself.
- Failing to record inference parameters, making reruns non-reproducible.

### Stretch goals

- Add OpenTelemetry trace IDs to local traces.
- Generate a tiny static HTML report from sample traces.

---

## Week 4 — Bedrock Model Evaluations: Managed Judge Jobs

### Objective

Prepare and run the model evaluation lane using Bedrock Evaluations.

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
   - from internal trace format;
   - to Bedrock model evaluation JSONL.
2. Create a BYOI model evaluation adapter:
   - one model response per prompt;
   - one model identifier per job;
   - job fan-out plan for multi-model comparisons.
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
- Multi-model comparison is represented as multiple job manifests plus a summarizer, not one magical job.
- Output handling expects S3 result artifacts, not console screenshots.

### Public-safe artifacts to commit

- `src/adapters/bedrock_model_eval.py`
- `infra/templates/bedrock-model-eval-job.json`
- `docs/week-04-model-evals-runbook.md`

### Common failure modes

- Overclaiming that Bedrock model eval jobs are a universal benchmark runner.
- Ignoring prompt count limits.
- Forgetting that judge models and rubrics are versioned dependencies.
- Forgetting that evaluator-model and metric availability vary by region, and that every job bills real tokens — bound dataset size and tag the job.

### Stretch goals

- Build a local summarizer that compares two completed job result folders.
- Add confidence interval calculations for repeated runs.

---

## Week 5 — Custom Metrics and Judge Rubric Engineering

### Objective

Design, validate, and version custom LLM-as-judge metrics.

### Why it matters

A judge prompt is production logic. Treat it like code, not a magic incantation whispered into the cloud goblin.

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
   - refusal appropriateness.
2. For each rubric, define:
   - purpose;
   - allowed scores;
   - judge instructions;
   - output schema;
   - examples of good/bad judgments.
3. Build a calibration dataset:
   - 50 synthetic examples;
   - human labels;
   - expected failure labels.
4. Write a judge validation notebook or script:
   - judge-vs-human agreement;
   - inter-rater agreement beyond raw accuracy (e.g. Cohen's kappa), so chance agreement does not flatter the judge;
   - confusion matrix;
   - false positives/false negatives;
   - variance across reruns;
   - bias probes for position and verbosity effects, plus self-preference when the judge shares a model family with the candidate.

### Validation checks

- Each rubric has a version and owner.
- Judge outputs are machine-parseable.
- Human labels are stored separately from generated model outputs.
- You can identify which labels the judge gets wrong.
- No judge gates anything until it clears a documented agreement bar against human labels.

### Public-safe artifacts to commit

- `rubrics/*.md`
- `schemas/judge-output.schema.json`
- `datasets/synthetic/human-labels.jsonl`
- `scripts/judge_calibration_report.py`
- `docs/judge-validation.md`

### Common failure modes

- Treating judge scores as truth instead of measurements with error bars.
- Reporting raw agreement while ignoring chance agreement, judge drift across evaluator-model versions, and position/verbosity bias.
- Writing vague rubrics that produce pretty prose but no usable score.
- Forgetting that AWS custom metrics may not visualize as expected without output schema/rating scale structure.
- Building the harmlessness/refusal calibration set out of genuinely operational harmful prompts — synthetic is not the same as safe. Keep committed examples non-operational (category labels, not working instructions); see Working Assumptions.

### Stretch goals

- Compare two evaluator models.
- Add bootstrap confidence intervals.

---

## Week 6 — Bedrock RAG Evaluations: Retrieval and Retrieve-and-Generate

### Objective

Build the RAG evaluation lane with both retrieval-only and end-to-end retrieve-and-generate datasets.

### Why it matters

RAG failures split into retrieval failures and generation failures. If you only score the final answer, you will blame the wrong subsystem.

### AWS services/docs to study

- Bedrock Knowledge Base evaluation
- Retrieval-only custom RAG evaluation
- Retrieve-and-generate custom RAG evaluation
- RAG metrics: context relevance, context coverage, correctness, completeness, faithfulness, harmfulness, answer refusal, citation precision, citation coverage (treat this list as illustrative — confirm the metric names and availability currently offered in the linked RAG evaluation docs)

### Build tasks

1. Create synthetic RAG corpus and questions.
2. Build adapters for:
   - retrieval-only BYOI;
   - retrieve-and-generate BYOI;
   - internal trace to Bedrock RAG JSONL.
3. Add a retrieval diagnostic report:
   - top-k retrieved passages;
   - expected supporting passage;
   - missing-context failures;
   - irrelevant-context failures.
4. Write `docs/rag-eval-runbook.md`.

### Validation checks

- Retrieval-only metrics can be interpreted separately from answer metrics.
- The custom RAG dataset uses one RAG source per job.
- References and retrieved passages are synthetic and safe.
- Citation metrics are only used when citation structures exist.

### Public-safe artifacts to commit

- `datasets/synthetic/rag-corpus.md` or JSONL equivalent
- `src/adapters/bedrock_rag_eval.py`
- `scripts/rag_diagnostics.py`
- `docs/rag-eval-runbook.md`

### Common failure modes

- Collapsing retrieval quality and generation quality into one vague score.
- Missing the required RAG-source identifier in custom RAG BYOI output (confirm the exact field name, e.g. `knowledgeBaseIdentifier`, in the linked dataset docs).
- Comparing multiple RAG systems in one managed job instead of orchestrating separate jobs.

### Stretch goals

- Add an adversarial RAG set with distractor documents.
- Add a “retrieval changed but answer did not” analysis.

---

## Week 7 — Deterministic Scorers and Lightweight Lambda Glue

### Objective

Build deterministic scorers that complement LLM judges.

### Why it matters

LLM judges are flexible. Deterministic scorers are boring in the best possible way. You want both.

### AWS services/docs to study

- Lambda for lightweight validation and dispatch
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
   - tool-call argument shape.
2. Package scorers as local CLI functions first.
3. Design Lambda wrappers for lightweight scoring tasks.
4. Define when **not** to use Lambda:
   - long-running evals;
   - large batch processing;
   - heavy model/tool simulations;
   - complex Inspect AI tasks.

### Validation checks

- Scorers are deterministic and unit-tested.
- Scorer outputs include version, inputs, score, and explanation.
- Lambda design does not pretend every workload fits inside Lambda limits.

### Public-safe artifacts to commit

- `src/scorers/*.py`
- `tests/test_scorers.py`
- `docs/scorer-library.md`
- `infra/templates/lambda-scorer-wrapper.md`

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

Make agent/tool evaluation first-class using Amazon Bedrock AgentCore Evaluations patterns.

### Why it matters

Agent eval is not just “did the final answer sound okay?” You need traces: tool choice, arguments, order, recovery behavior, safety boundaries, and state transitions. The durable, checkable artifact this week is a trace adapter plus synthetic traces that validate against your agent-trace schema and a set of evaluator specs — not a live managed agent eval.

### AWS services/docs to study

- Bedrock AgentCore Evaluations
- OpenTelemetry and OpenInference trace concepts
- Strands and LangGraph integration patterns
- Evaluation modes and framework integrations as currently documented — AgentCore Evaluations is newer and evolving, so confirm exact mode names, supported integrations, and trace formats in the linked doc rather than trusting this list

### Build tasks

1. Define an agent task suite:
   - tool selection;
   - tool argument validity;
   - multi-turn state tracking;
   - safe refusal;
   - recovery from tool failure;
   - prompt-injection resistance.
2. Create synthetic OpenTelemetry/OpenInference-style trace examples.
3. Build an adapter from internal traces to an AgentCore-friendly format.
4. Define custom agent evaluators:
   - wrong tool;
   - unsafe tool call;
   - missing confirmation;
   - hallucinated external action;
   - failed recovery.
5. Write `docs/agentcore-evals-runbook.md`.

### Validation checks

- Agent tasks inspect trace behavior, not only final text.
- Tool-call arguments are checked deterministically where possible.
- Safety evals distinguish “refused safely” from “failed to complete.”
- Simulation mode is treated as useful but not equivalent to production behavior.
- Synthetic traces validate against `schemas/agent-trace.schema.json`, so this lane has a checkable artifact even without a live AgentCore job.

### Public-safe artifacts to commit

- `agentcore/trace-examples/*.json`
- `agentcore/evaluators/*.md`
- `src/adapters/agent_trace_adapter.py`
- `docs/agentcore-evals-runbook.md`

### Common failure modes

- Treating agents as chatbots with extra steps.
- Ignoring tool arguments and side effects.
- Committing real agent traces — tool inputs/outputs and intermediate state routinely carry sensitive data; keep repo traces synthetic and redacted.
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
   - model-only reasoning;
   - RAG answer checking;
   - agent/tool-use replay.
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

## Week 10 — Orchestration, Manifests, and Reproducible Runs

### Objective

Build the orchestration layer that turns individual eval pieces into repeatable runs.

### Why it matters

A harness is the system that runs evals the same way twice, explains what changed, and leaves evidence behind.

### AWS services/docs to study

- Step Functions
- EventBridge
- S3 object versioning
- Glue/Athena
- CodeBuild for CI-style execution

### Build tasks

1. Design a Step Functions workflow:
   - validate dataset;
   - generate or import candidate responses;
   - dispatch Bedrock model eval jobs;
   - dispatch RAG eval jobs;
   - dispatch AgentCore evals;
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
- Re-running the same synthetic input produces comparable outputs.
- Failures are captured as structured states, not lost terminal output.
- Managed-job IDs are persisted in the manifest so result artifacts can be fetched and re-summarized later.
- A retried run is idempotent or resumable: it reuses its run ID and does not silently double-bill managed jobs.

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
- Cost Explorer and cost allocation tags
- IAM least privilege and KMS encryption

### Build tasks

1. Add local CI checks:
   - dataset validation;
   - unit tests;
   - public-safety scan;
   - markdown/link checks if available.
2. Define regression gates:
   - deterministic scorer thresholds;
   - judge score thresholds;
   - allowed confidence interval movement;
   - cost/latency budgets.
3. Design AWS CI/CD path:
   - CodeBuild or GitHub Actions OIDC;
   - deploy/update eval infrastructure;
   - trigger scheduled eval runs;
   - publish summary report.
4. Write `docs/regression-gates.md` and `docs/cost-controls.md`.

### Validation checks

- CI fails on invalid datasets.
- CI fails on unsafe public examples.
- Regression gates are documented with rationale.
- Cost controls separate experiment budget from production monitoring.
- Every eval job is tagged and records a per-run cost estimate in its manifest; a max-dataset-size / max-fan-out guardrail stops a typo from launching a thousand jobs.
- Committed IAM/KMS templates use scoped, per-lane roles and a customer-managed KMS key — no wildcard (`*`) actions or resources.

### Public-safe artifacts to commit

- `.github/workflows/validate.yml` or equivalent placeholder workflow
- `docs/regression-gates.md`
- `docs/cost-controls.md`
- `scripts/check_regression_gate.py`

### Common failure modes

- Setting arbitrary thresholds without calibration.
- Letting eval cost grow invisibly.
- Shipping IAM policies with wildcard actions/resources because least privilege is annoying.
- Treating CloudWatch alarms as quality evals instead of operational signals.

### Stretch goals

- Add a small synthetic “before/after” report showing a regression caught by CI.
- Add cost-per-eval-run estimates.

---

## Week 12 — Capstone: AWS Eval Harness Reference Architecture

### Objective

Package the whole thing into a deployable, reviewable, public-safe reference architecture.

### Why it matters

This is the artifact that says: “I do not merely know eval words. I can build the machine.”

### AWS services/docs to study

Review everything from Weeks 1-11, then focus on integration gaps.

### Build tasks

1. Assemble the capstone package:
   - CDK or Terraform stack skeleton;
   - S3 bucket layout;
   - IAM/KMS policy placeholders;
   - Step Functions workflow;
   - Lambda scorer wrappers;
   - SageMaker/ECS/Batch custom eval runner option;
   - Bedrock model eval job templates;
   - Bedrock RAG eval job templates;
   - AgentCore evaluator config/examples;
   - Inspect AI recipe/task;
   - schemas and validators;
   - run manifest and result summarizer;
   - dashboards/runbooks;
   - public-safe report.
2. Run an end-to-end synthetic local harness run.
3. If using an AWS sandbox account, run one minimal live cloud path and keep live output out of the repo.
4. Publish a final report under `docs/reports/capstone.md` with:
   - what was built;
   - what was validated;
   - what was not validated;
   - cost/security assumptions;
   - known limitations;
   - next steps.

### Validation checks

- A reviewer can clone the repo and understand the architecture without private context.
- Local synthetic validation passes.
- Cloud instructions use placeholders only.
- Claims match evidence.
- The public report does not imply production security, universal correctness, or magic eval truth.

### Public-safe artifacts to commit

- `docs/reports/capstone.md`
- `docs/runbook.md`
- `infra/README.md`
- `src/README.md`
- final schemas, adapters, validators, scorers, templates, and reports

### Common failure modes

- Publishing cloud screenshots or logs with identifiers.
- Saying “production-ready” when only synthetic local tests ran.
- Letting the capstone become a pile of disconnected files instead of a harness.

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
  - synthetic RAG dataset;
  - agent/tool task dataset;
  - human-label calibration set;
  - dataset schemas and validators.
- **Adapter layer**
  - internal trace to Bedrock model eval;
  - internal trace to Bedrock RAG eval;
  - internal trace to AgentCore-friendly trace format;
  - Inspect result adapter;
  - run manifest writer.
- **Scoring layer**
  - deterministic scorer library;
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
  - cost tagging strategy;
  - CloudTrail/audit notes;
  - runbook.
- **Evidence layer**
  - public-safe capstone report;
  - synthetic run summary;
  - limitations section;
  - source ledger.

## Decision Matrix

| Need | Prefer | Why |
| --- | --- | --- |
| Judge model answers against a rubric | Bedrock Model Evaluation | Managed scoring, built-in/custom metrics, S3-backed jobs |
| Score BYOI model responses | Bedrock Model Evaluation BYOI | Useful when candidate outputs are generated outside Bedrock |
| Score retrieval quality | Bedrock RAG retrieval evaluation | Separates retrieval from generation failures |
| Score RAG answer quality | Bedrock RAG retrieve-and-generate evaluation | Uses RAG-specific metrics such as faithfulness and citation coverage |
| Evaluate tool calls and multi-turn agent behavior | Bedrock AgentCore Evaluations | Designed around agent/tool traces and evaluator modes |
| Run complex programmatic evals | Inspect AI on SageMaker/ECS/Batch | Eval logic is code, not only judge prompts |
| Validate data and run lightweight scoring | Lambda or local CLI | Fast glue, schema checks, deterministic scoring |
| Coordinate many jobs | Step Functions | Explicit state, retries, failure handling, auditability |
| Query historical results | S3 + Glue/Athena | Cheap evidence lake pattern |
| Block regressions in development | CI/CD regression gates | Converts evals into shipping discipline |

> The managed Bedrock rows still leave you owning dataset prep, job fan-out, summarization, and judge validation. “Managed” scopes the scoring runtime, not the harness.

## What Not to Overclaim

Do not claim:

- “Bedrock Evaluations is the whole harness.” It is a managed evaluation component.
- “BYOI evaluates any live app automatically.” BYOI means you provide inference responses in the expected schema.
- “LLM-as-judge is ground truth.” It is a judge with measurable error.
- “Synthetic tests prove production safety.” They prove behavior on synthetic tests.
- “Agent simulation equals production behavior.” It is useful evidence, not a deployment guarantee.
- “A passing eval means the model is safe.” It means it passed a scoped test suite.
- “One RAG score explains everything.” Retrieval and generation failures must be separated.
- “Serverless means Lambda for everything.” Heavy eval workloads often belong in SageMaker, ECS, Batch, or managed Bedrock jobs.
- “No private data in repo means no privacy risk.” Cloud logs and S3 outputs can still contain sensitive data.
- “Same prompt, same score.” Hosted models are not guaranteed deterministic even at temperature 0; pin versions, expect drift, and re-baseline — reproduce the *harness*, not the model's every token.
- “A managed eval job verifies correctness.” It applies your dataset and chosen metrics; a model-as-judge still does the scoring, with error.

## Suggested Weekly Rhythm

Use the same loop every week:

1. Read the relevant AWS docs.
2. Add or update schemas.
3. Build a tiny synthetic example.
4. Validate locally.
5. Add a runbook.
6. Add a public-safe report or screenshot-free receipt.
7. Run public-safety scan.
8. Commit only the safe artifacts.

## Source Ledger

Primary AWS references to consult while building this plan:

- Amazon Bedrock Evaluations: <https://aws.amazon.com/bedrock/evaluations/>
- Model evaluation prompt datasets for model-as-judge: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-prompt-datasets-judge.html>
- Custom metrics for model evaluation jobs: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-custom-metrics-create-job.html>
- Knowledge Base retrieve-and-generate prompt datasets: <https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-evaluation-prompt-retrieve-generate.html>
- Custom RAG retrieve-and-generate evaluation: <https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-evaluation-create-randg-custom.html>
- Custom retrieval-only evaluation: <https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-evaluation-create-ro-custom.html>
- Bedrock model invocation logging: <https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html>
- Bedrock AgentCore Evaluations: <https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations.html>
- SageMaker Inspect AI container: <https://docs.aws.amazon.com/nova/latest/userguide/nova-eval-inspect-ai-container.html>

These pages are the source of truth for schemas, field names, metric lists, job constraints, and evaluation modes. This plan paraphrases them to stay readable; where the two disagree, follow the docs, and assume AWS has shipped changes since this was written.

## Final Standard

The final artifact should make one thing obvious: you can build AWS eval infrastructure with adult supervision. Not “I prompted a judge model once.” Not “I made a dashboard.” A real harness: versioned inputs, scoped claims, repeatable runs, calibrated judges, deterministic checks, traceable outputs, cost visibility, and public-safe receipts.
