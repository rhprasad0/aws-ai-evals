# AWS AI Evals: 12-Week Hands-On Learning Plan

This is a learning-by-doing path for building an AWS-native and hybrid AI evaluation harness around a real production experiment: a public **ryanprasad.ai candidate evidence chatbot**. The goal is not to click around the Bedrock console and declare victory. The goal is to build a small but serious reference architecture: security and access preflight, datasets, schemas, validators, managed Bedrock eval jobs, RAG evals, Inspect AI custom evals, orchestration, observability, quota-based cost controls, and public-safe reports.

Bedrock Evaluations gives you managed scoring, comparison, and reporting workflows for supported model and RAG paths. The harness you build around them handles preflight, validation, versioning, CI/CD glue, unsupported scorers, normalized exports, and public-safe evidence beyond the managed outputs.

## Production Experiment: ryanprasad.ai Candidate Agent

The live specimen is a public chatbot exposed on `ryanprasad.ai`. It should:

- answer recruiter-style questions about Ryan's public GitHub projects from public/project-safe sources, with citations;
- map skills to public evidence, starting with questions like “Where does Ryan show container orchestration?”;
- distinguish strong evidence, lab/project evidence, weak support, and unsupported claims;
- refuse unsupported, private, unsafe, or ambiguous requests.

RAG stays first: project Q&A is the main user value and the easiest place to build citation-backed evidence. Calendar booking, Slack relay, and other tool-use flows are out of scope for this 12-week iteration. V1 keeps the app boring so the eval harness is the main work.

Product boundaries:

- No private memory, Honcho, Graphiti, local notes, private transcripts, or private repo content may appear in public answers unless explicitly curated into public-safe docs.
- No Calendar, Slack, or other tool writes in this iteration.
- GitHub/project Q&A must cite public sources and say "I don't know" when support is missing.
- Evidence strength must be explicit: public artifact, lab/project artifact, WIP, weak support, or unsupported.

## Second Iteration: Evals Before Deployment

The previous iteration moved too quickly from chatbot implementation into cloud eval machinery. This pass reverses that order. The first milestone is not a polished deployed chatbot; it is a checkable evaluation contract: schemas, synthetic datasets, human-label workflow, deterministic gates, judge calibration, and a minimal specimen that can produce traceable answers.

Deployment and product polish stay behind an eval-contract gate. Before treating the chatbot as a public artifact, the repo should prove that local evals can say useful things about citations, evidence strength, refusals, unsupported claims, and public/private source boundaries.

AgentCore and tool-use evaluation activities are intentionally discarded from this iteration. Future Calendar, Slack, or write-action tools can get their own plan after the model, RAG, labeling, and reporting foundations are boring.

## North Star

By the end of 12 weeks, you should have a deployable **AWS Eval Harness Reference Architecture** that can:

- evaluate the `ryanprasad.ai` candidate evidence chatbot across public project Q&A, citation support, evidence calibration, refusal, and abuse-handling flows;
- evaluate model outputs with Amazon Bedrock Evaluations;
- evaluate RAG retrieval and retrieve-and-generate pipelines;
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

**Synthetic is not the same as safe.** The safety, refusal, and prompt-injection lanes generate *attacks* by design. In a public, billboard-safe repo, keep that content non-operational: name the attack class and use inert canaries (e.g. `INJECTION_CANARY_DO_NOT_FOLLOW`), never working jailbreaks, exploit code, or copy-pasteable harmful instructions. The rules above keep *real* data out; this one keeps *dangerous* content out. An eval repo must not double as an attack cookbook.

### Terms and source of truth

- **BYOI = Bring Your Own Inference responses.** For Bedrock model evaluation BYOI, you supply `modelResponses` in AWS's expected dataset shape. Amazon Bedrock skips the model-invoke step and evaluates the supplied responses. For V1, generate chatbot answers first, keep raw Bedrock invocation logs in same-Region S3 for lab analysis, and normalize selected outputs into BYOI datasets. Do not assume a Bedrock model-eval job directly calls arbitrary live endpoints unless the current AWS docs say so for that exact path.
- **The Source Ledger is the source of truth.** This plan paraphrases AWS schemas, field names, metric lists, job constraints, and evaluation modes so you can build against them — but AWS evolves these, and paraphrases drift. Confirm specifics against the linked docs before wiring anything up. When this plan and the docs disagree, the docs win.

## Architecture Lanes

Treat these as separate lanes that converge in the capstone:

1. **Model evaluation lane** — Bedrock model evaluation jobs, model-as-judge, built-in metrics, custom metrics, BYOI model responses.
2. **RAG evaluation lane** — Bedrock Knowledge Base retrieval-only and retrieve-and-generate evaluation for Ryan's public/project-safe GitHub corpus, native comparison/reporting for supported RAG sources/configurations, plus custom RAG BYOI datasets where you supply supported response data.
3. **Custom harness lane** — Inspect AI, deterministic scorers, schema validators, custom task runners, SageMaker/ECS/Batch execution.
4. **Platform lane** — S3, KMS, IAM, Step Functions, small Lambda glue, CloudWatch, CloudTrail, Athena/Glue, Service Quotas, Cost Explorer/Budgets, CI/CD.

Lanes 1–3 are the **evaluation lanes**; lane 4 is cross-cutting glue. Lanes 1–2 lean on *managed* Bedrock jobs — you own preflight, dataset and trace preparation, manifesting, validation, and interpretation; AWS owns the supported scoring/reporting runtime. Start with native Bedrock comparison and reporting workflows where they fit. Add custom orchestration for preflight, versioning, CI/CD, unsupported scorers, repeated-run analysis, cross-service aggregation, and reporting beyond managed outputs. Lane 3 is code you run yourself. Keep their datasets, schemas, and result shapes separate; they only converge at the orchestration and reporting layer, and a score from one lane does not transfer to another.

## Managed Job Boundaries (Read Before Week 4)

Bedrock model and RAG evaluations are *managed jobs*, not a magic verdict service. Before you lean on them, internalize the edges:

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
  scripts/
    public_safety_scan.py
    validate_dataset.py
    summarize_run.py
```

This plan starts documentation-first, then turns it into code and deployable infrastructure.

---
## Week 1 — Simplified Eval/Product Contract and Repo Posture

### Objective

Define the public `ryanprasad.ai` candidate evidence chatbot as a deliberately boring lab specimen with one source file, one coarse labeling workflow, and no premature cloud or citation machinery.

### Why it matters

The previous iteration made the contract hard to label by introducing too many axes too early: citations, source labels, evidence-strength taxonomies, run manifests, managed-job assumptions, and detailed security/IAM scaffolding before the local evaluation shape was stable. This reset keeps Week 1 focused on the contract that humans can actually label: `profile.md` is the only source, responses are minimal JSON, labels are pass/fail, and production AI experience is the central recruiter probe.

The key recruiter truth is that Ryan does not currently have production AI experience. The chatbot should answer that directly and pivot to adjacent GitHub-backed AI engineering, eval, AWS, and agent/tooling evidence. It must not invent shipped production AI systems, customer-scale operation, on-call ownership, or live AI deployments.

### AWS services/docs to study

Light-touch only in Week 1:

- Amazon Bedrock Converse structured-output behavior, enough to understand future minimal JSON responses.
- Amazon Bedrock Evaluations overview, enough to know what is deferred until local labels exist.

Do not design IAM/KMS/S3/service-role infrastructure in Week 1. That belongs later if managed Bedrock jobs become concrete.

### Build tasks

1. Write `docs/evaluability-design-doc.md` with the simplified contract:
   - `profile.md` is the only chatbot source;
   - GitHub is upstream evidence, but not retrieved at answer time;
   - no source ledger, citation policy, evidence-strength taxonomy, or full run manifest;
   - request classes: `answerable_public_evidence`, `unsupported_or_overclaim`, `off_topic_or_abuse`;
   - expected behaviors: `answer_with_public_evidence`, `answer_with_caveat`, `say_not_supported`, `refuse_or_redirect`;
   - human labels: `pass` or `fail`, with optional failure tags;
   - captured responses: metadata plus minimal `response.answer` and optional `response.responseKind`;
   - production AI experience probes are first-class examples;
   - public-safe artifact policy for what can and cannot be committed.
2. Write `docs/architecture.md` as a tiny architecture sketch:
   - `profile.md` -> prompt wrapper -> model -> minimal JSON response -> captured response -> pass/fail human label;
   - no retrieval, no tools, no memory, no citations, no cloud eval jobs, and no deployment architecture yet.
3. Record the next build artifacts for Week 2:
   - `profile.md`;
   - dataset schema;
   - captured-response schema;
   - human-label schema;
   - first small synthetic dataset;
   - validator script;
   - public-safety scan.

### Validation checks

- A new contributor can explain the chatbot source boundary: answers come from `profile.md` only.
- A new contributor can explain the labeling workflow: one row, one response, one pass/fail label.
- The doc makes production AI candor explicit and treats production-AI overclaiming as a failure.
- The design does not require source ledgers, citations, evidence-strength labels, run manifests, AWS IAM/KMS scaffolding, Bedrock jobs, RAG, UI work, or deployment before the first labels exist.
- Public/private boundaries are stated as repo artifact hygiene and source curation, not as a live-memory leakage threat.
- `git diff --check` passes.

### Public-safe artifacts to commit

- `docs/evaluability-design-doc.md`
- `docs/architecture.md`

### Common failure modes

- Reintroducing the previous iteration's citation/source-label/evidence-strength schema before labels exist.
- Treating production AI experience as an embarrassing edge case instead of the main recruiter question.
- Building Bedrock/IAM/S3 infrastructure before the local contract is labelable.
- Letting `profile.md` become vague marketing copy instead of a concise evidence file with claim limits.
- Treating GitHub as runtime retrieval instead of upstream evidence summarized in `profile.md`.

### Stretch goals

- Add a one-page candidate-agent product contract that a recruiter can skim.

---
## Week 2 — Profile Source, Coarse Schemas, and Validators

### Objective

Turn the Week 1 design into a small local workflow: write `profile.md`, define coarse schemas, create a first synthetic recruiter-evidence dataset, and validate everything locally before building the chatbot.

### Why it matters

The chatbot should not exist before the source and labels are clear. Week 2 proves that the profile-only source boundary and pass/fail labeling workflow are concrete enough to validate. This is where public-safety scanning belongs: after there are actual schemas, fixtures, and datasets to scan.

### AWS services/docs to study

- Bedrock Converse API JSON response behavior, only as future implementation context.
- JSON Schema conventions for local validation.

Managed Bedrock evaluation jobs, BYOI exports, RAG evals, and judge rubrics remain deferred.

### Build tasks

1. Write `profile.md`:
   - summarize GitHub-backed evidence only;
   - include explicit claim limits;
   - include a direct production AI experience statement;
   - state that there are no live AI projects currently up;
   - avoid unsupported production/customer/scale/on-call claims.
2. Create JSON Schemas for:
   - `schemas/eval-example.schema.json`;
   - `schemas/captured-response.schema.json`;
   - `schemas/human-label.schema.json`.
3. Create tiny valid and invalid fixtures for each schema.
4. Create `datasets/synthetic/recruiter-evidence-qa.jsonl` with a small first slice:
   - production AI experience probes;
   - GitHub-backed adjacent evidence questions;
   - unsupported/overclaim prompts;
   - off-topic or inert prompt-injection canaries.
5. Build `scripts/validate_dataset.py`:
   - validates JSON and JSONL;
   - reports line numbers and schema paths;
   - checks enum values and required fields;
   - validates fixture files and the first synthetic dataset.
6. Add `scripts/public_safety_scan.py` as a simple repo scanner for public artifacts:
   - secrets/token-shaped strings;
   - private/local paths;
   - AWS identifiers;
   - private hostnames/IPs;
   - raw traces or provider-output markers.

### Validation checks

- `profile.md` is public-safe and contains no private/local/source-of-truth leakage.
- Valid fixtures pass and invalid fixtures fail with clear errors.
- The first synthetic dataset validates.
- Human labels remain binary: `pass` or `fail`.
- Captured response schema stays minimal: metadata plus `response.answer` and optional `response.responseKind`.
- The public-safety scan runs over tracked docs, schemas, fixtures, datasets, and scripts.
- No chatbot, UI, deployment, Bedrock job, citation policy, source ledger, or run-manifest system is introduced.

### Public-safe artifacts to commit

- `profile.md`
- `schemas/eval-example.schema.json`
- `schemas/captured-response.schema.json`
- `schemas/human-label.schema.json`
- `datasets/synthetic/recruiter-evidence-qa.jsonl`
- schema fixtures under a test fixture directory
- `scripts/validate_dataset.py`
- `scripts/public_safety_scan.py`

### Common failure modes

- Writing `profile.md` like a résumé instead of an evidence/claim-limit source file.
- Letting production AI answers become vague positioning instead of candid no-plus-adjacent-evidence answers.
- Adding citations, source labels, evidence-strength labels, or judge rubrics before pass/fail labels are proven useful.
- Making the dataset too large to label in one sitting.
- Treating the public-safety scanner as a substitute for human review.

### Stretch goals

- Add a tiny CLI summary showing dataset counts by `requestClass`, `expectedBehavior`, `sourceSupport`, and `productionAiProbe`.

---
## Week 3 — Minimal Profile-Only Specimen

### Objective

Create the smallest local candidate-agent specimen needed to turn a dataset row plus `profile.md` into the minimal JSON response defined in Week 1 and Week 2.

### Why it matters

The first implementation should prove the contract, not become a product. The specimen only needs to show that the prompt wrapper, `profile.md`, model call, captured response wrapper, and validator can work together. It should not add retrieval, citations, source labels, evidence-strength labels, UI polish, or deployment work.

### AWS services/docs to study

- Bedrock Converse API response structure
- Bedrock JSON / structured-output behavior where applicable

### Build tasks

1. Define the specimen interface:
   - input `question` from a dataset row;
   - `profile.md` loaded as the only evidence source;
   - prompt wrapper with clear profile delimiters;
   - model response JSON with `answer` and optional `responseKind`.
2. Implement a local runner that:
   - reads the small synthetic dataset;
   - calls the model for each row or supports a stub mode for fixture testing;
   - writes captured response records with `exampleId`, `runId`, `capturedAt`, `modelId`, `promptVersion`, `profileVersion`, and `response`.
3. Validate captured responses against `schemas/captured-response.schema.json`.
4. Keep production AI probes in the smoke set.
5. Document how to run the local specimen without deploying anything.

### Validation checks

- The runner can produce valid captured response JSON for a small dataset slice.
- Production AI questions receive candid no-plus-adjacent-evidence answers, not production overclaims.
- Unsupported/overclaim prompts can produce `not_supported` or caveated answers.
- Off-topic or inert prompt-injection canaries can produce `refusal` or redirect-style answers.
- No citations, source labels, evidence-strength labels, run manifests, retrieval, UI, deployment, or Bedrock managed jobs are introduced.

### Public-safe artifacts to commit

- minimal local runner or specimen module
- captured-response fixture(s)
- docs for local run instructions

### Common failure modes

- Turning the specimen into a public chatbot before labels are useful.
- Adding retrieval because `profile.md` is imperfect instead of improving `profile.md`.
- Treating `responseKind` as the label.
- Hiding the production AI limitation behind vague positioning.

### Stretch goals

- Add a tiny report that prints pass/fail placeholder counts once human labels exist.

---
## Week 4 — Local Harness and Mechanical Gates

### Objective

Build the local harness that connects datasets, captured responses, human labels, and simple mechanical validation. Keep the gates schema-focused; do not recreate citation or rubric scoring.

### Why it matters

The local harness should make it cheap to rerun the profile-only specimen and see whether the workflow still holds together. Mechanical gates catch malformed data. Human labels judge answer quality.

### AWS services/docs to study

None required. This week can remain local unless a concrete Bedrock integration is ready.

### Build tasks

1. Add local commands to:
   - validate dataset rows;
   - validate captured responses;
   - validate human labels;
   - join examples, responses, and labels by `exampleId`.
2. Add a simple summary report:
   - total examples;
   - pass/fail counts;
   - failure-tag counts;
   - production-AI probe pass/fail counts;
   - missing response or missing label counts.
3. Keep deterministic checks mechanical:
   - valid JSON/JSONL;
   - required fields;
   - enum values;
   - unique IDs;
   - captured responses include `response.answer`.
4. Add fixture tests for the validator and summary command.

### Validation checks

- The harness can validate the first dataset, response fixture, and label fixture.
- The summary report is generated from local files.
- Pass/fail remains a human label, not a model-generated or deterministic score.
- No citation scoring, evidence-strength scoring, source ledger checks, full manifests, Bedrock jobs, or deployment work are introduced.

### Public-safe artifacts to commit

- local harness command(s)
- summary/report script
- tests or fixtures for the local workflow

### Common failure modes

- Turning mechanical validation into a hidden rubric.
- Reintroducing old citation/evidence-strength gates.
- Reporting model quality from unlabeled responses.
- Expanding the dataset faster than it can be manually reviewed.

### Stretch goals

- Emit a small Markdown summary suitable for a future public report.

---
## Week 5 — Human Labeling Workflow

### Objective

Build the lightweight human-label workflow around binary `pass`/`fail` labels and optional failure tags.

### Why it matters

Human labels are the calibration center. Keep them simple enough that Ryan can review a small dataset in one sitting. If labels become slow or ambiguous, fix the dataset and contract before adding judge rubrics.

### AWS services/docs to study

None required. Managed human evaluation concepts can wait until there is a local label set worth scaling.

### Build tasks

1. Create or extend a small local label-review workflow that shows:
   - dataset row;
   - `profile.md` reference context as needed;
   - captured response;
   - `pass` / `fail` choice;
   - optional failure tags;
   - optional review notes.
2. Validate labels against `schemas/human-label.schema.json`.
3. Add a summary command for:
   - pass/fail counts;
   - failure-tag counts;
   - production-AI probe results;
   - unlabeled or duplicate labels.
4. Use the workflow on the first small dataset.

### Validation checks

- Labels are binary: `pass` or `fail`.
- Failure tags are optional diagnosis, not separate rubric scores.
- Production AI probes are easy to review for candor versus overclaim.
- Rows that are hard to label are revised rather than patched with more rubric complexity.

### Public-safe artifacts to commit

- label workflow script or docs
- reviewed human-label fixture or first reviewed label file
- summary output example if public-safe

### Common failure modes

- Reintroducing `needs_review`, partial credit, or multi-rubric scoring too early.
- Letting `responseKind` override human judgment.
- Treating unlabeled responses as evaluated results.

### Stretch goals

- Add a tiny browser or terminal UI if plain JSONL review becomes annoying.

---
## Week 6 — Optional Judge Calibration from Binary Labels

### Objective

Decide whether a judge is needed at all. If the binary human labels are stable and useful, prototype a small judge-calibration path against those labels. Do not create a multi-rubric suite by default.

### Why it matters

A judge prompt is production logic. The reset plan should earn judge complexity from observed labeling pain, not assume it up front. The first judge question is simple: can a model predict Ryan's `pass`/`fail` label well enough to reduce manual review for this narrow profile-only chatbot?

### AWS services/docs to study

- Bedrock custom metric concepts, only if a local judge prototype is useful.
- Model-as-judge calibration patterns.

### Build tasks

1. Review the first human-label set and identify whether manual labeling is actually a bottleneck.
2. If yes, draft one binary judge prompt:
   - input: dataset row, `profile.md` excerpt or full profile, captured response;
   - output: predicted `pass` or `fail`, optional failure tags, short rationale.
3. Compare judge predictions against human labels:
   - agreement rate;
   - false-pass examples, especially production AI overclaims;
   - false-fail examples, especially candid caveated answers.
4. Keep generated judge outputs separate from human labels.

### Validation checks

- Human labels remain the source of truth.
- Judge output never overwrites human labels.
- Calibration focuses on binary pass/fail first.
- Production AI overclaim false-passes are treated as serious failures.
- No broad correctness/completeness/citation/evidence-strength rubric suite is introduced unless the label set proves it is needed.

### Public-safe artifacts to commit

- optional judge prompt draft
- optional judge-output schema
- calibration summary using public-safe examples

### Common failure modes

- Building a judge system before there is enough human-label data.
- Treating judge agreement as truth instead of a measurement.
- Adding rubric dimensions that humans are no longer labeling.

### Stretch goals

- Compare two judge models on the same binary-label set if the first judge is useful.

---
## Week 7 — Bedrock Model Evaluations: Managed Judge Jobs

### Objective

Prepare and run the model evaluation lane using Bedrock Evaluations for candidate-agent responses that are not primarily retrieval checks.

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
   - one `modelResponses` entry per prompt;
   - one `modelIdentifier` value per job;
   - AWS-documented BYOI fields: `prompt`, optional `referenceResponse`, optional `category`, and `modelResponses[].response`/`modelResponses[].modelIdentifier`;
   - evidence that Bedrock skips model invocation for supplied `modelResponses`;
   - support for importing captured chatbot answers from Bedrock invocation logs and app traces as BYOI responses;
   - a native Bedrock comparison/reporting plan first, with separate manifests only where the selected API/BYOI path requires separate jobs.
3. Write a Bedrock model eval job template:
   - dataset S3 URI placeholder;
   - output S3 URI placeholder;
   - evaluator model placeholder;
   - built-in metric selection;
   - custom metric references.
4. Add `docs/week-07-model-evals-runbook.md` with CLI/SDK pseudocode and expected outputs.

### Validation checks

- Adapter output validates locally against the AWS-documented BYOI shape, including `prompt`, `referenceResponse`, `category`, and `modelResponses`.
- Job templates contain placeholders, not real account details.
- Candidate-agent examples are scoped to supported intents; raw captured outputs stay in lab S3 and normalized/public examples are safe to commit.
- Multi-model or multi-config comparison starts with Bedrock-native reports/comparison where supported; any extra manifests explain why custom coordination is needed.
- Output handling expects managed reports and S3 result artifacts, not console screenshots.

### Historical closeout note from the prior iteration

The prior iteration reached a Week 7-style live slice with the BYOI adapter, placeholder `create-evaluation-job` template, runbook, first-run receipt, and Terraform-managed Bedrock eval IAM role. A sandbox Bedrock model-as-judge BYOI job completed over captured chatbot responses, produced managed output JSONL, and confirmed the expected boundary: deterministic gates catch hard response-contract misses while Bedrock scores fuzzy correctness/completeness. Raw job outputs, real AWS identifiers, and S3 artifacts remain private/sandbox-only.

Carry into this evals-first ordering: repeated runs, stronger/independent judge comparison, human-label agreement, and variance analysis before any judge score becomes a regression gate.

### Public-safe artifacts to commit

- `src/adapters/bedrock_model_eval.py`
- `infra/templates/bedrock-model-eval-job.json`
- `docs/week-07-model-evals-runbook.md`
- `docs/week-07-model-evals-first-run.md`
- `infra/terraform/ryanprasad-chatbot/bedrock_eval.tf`

### Common failure modes

- Overclaiming that Bedrock model eval jobs are a universal benchmark runner.
- Ignoring prompt count limits.
- Forgetting that judge models and rubrics are versioned dependencies.
- Forgetting that evaluator-model and metric availability vary by region, and that every job bills real tokens — bound dataset size, check `ListFoundationModels`/model access/quotas, and estimate cost before submission.

### Stretch goals

- Build a local summarizer that compares two completed job result folders.
- Add confidence interval calculations for repeated runs.

---
## Week 8 — Bedrock RAG Evaluations: Retrieval and Retrieve-and-Generate

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
## Week 9 — Observability and Lab Trace Capture

### Objective

Instrument lab/eval runs so Bedrock invocation logs, chat turns, source labels, evidence-strength labels, refusals, latency, token/cost usage, and errors produce structured evidence.

### Why it matters

You cannot debug what you did not capture. Eval quality depends on trace quality. For this lab, Bedrock invocation logging is valuable because it captures the actual model request/response bodies and metadata. It still does not replace app traces: invocation logs do not know expected citations, evidence-strength labels, scorer results, source allowlists, deployment versions, or pass/fail status. The public repo gets schemas, examples, and normalized reports — raw invocation logs stay in lab S3.

### AWS services/docs to study

- Bedrock model invocation logging
- CloudWatch Logs and Logs Insights
- S3 object layout patterns
- CloudTrail audit events

### Build tasks

1. Enable Bedrock invocation logging for lab/eval runs to same-Region S3 only, with KMS encryption, text delivery enabled, non-text modalities disabled for V1, lifecycle expiration, and a placeholder bucket layout:
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
4. Preserve trace identifiers and request metadata sufficient to correlate app-level eval records with lab S3 invocation-log references.
5. Write `docs/observability.md`:
   - Bedrock invocation logging is enabled for lab/eval runs;
   - raw invocation logs are useful eval artifacts, not public report material;
   - same-Region S3 destination, run-prefix layout, lifecycle expiration, and access boundaries;
   - how the logging destination inherits prompt/response sensitivity (KMS-encrypt it, lock IAM, bound retention, keep it out of public artifact pipelines, and avoid CloudWatch delivery for raw model I/O);
   - CloudWatch/S3/Athena query plan;
   - how normalized trace exports and invocation-log-derived BYOI datasets feed Bedrock/RAG/Inspect eval lanes.
6. Add sample CloudWatch Logs Insights and Athena queries as documentation, using placeholders only.

### Validation checks

- Traces validate against your schema.
- A failed candidate call produces a structured error record.
- Public examples do not contain raw invocation logs, visitor content, live identifiers, or sensitive data.
- Evidence traces show source labels, citations, and evidence-strength labels.
- RAG/app traces contain citations for supported answers and refusal/"I don't know" outcomes for unsupported questions.
- Bedrock invocation logs can be correlated to app-level eval records by run ID or request metadata.
- Invocation logging uses S3-only delivery for raw model I/O; CloudWatch contains structured app events, not full prompts/responses.
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
- Treating the invocation-logging destination as plumbing when it actually holds full prompts and responses — a sensitive lab artifact store that needs KMS, lifecycle, least-privilege access, and separation from CloudWatch app logs.
- Failing to record inference parameters, making reruns non-reproducible.

### Stretch goals

- Add OpenTelemetry trace IDs to local traces.
- Generate a tiny static HTML report from sample traces.
- Add a sanitized production-trace summary format with no raw visitor content.

---
## Week 10 — Inspect AI and Custom Programmatic Evals

### Objective

Run advanced/custom evals with Inspect AI or equivalent custom runners on AWS infrastructure.

### Why it matters

Some evals are programs: multi-step tasks, sandboxed code checks, adversarial policies, and custom scoring logic. Managed judge jobs are not enough.

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
## Week 11 — Orchestration, CI, and Regression Gates

### Objective

Build the orchestration and CI layer that turns candidate-agent traces, datasets, and eval pieces into repeatable runs with regression gates.

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
   - dispatch Inspect/custom tasks;
   - aggregate results;
   - publish report.
2. Implement local workflow simulation:
   - use synthetic data;
   - create run manifest;
   - write result summary.
3. Create `schemas/run-result.schema.json`.
4. Add local CI checks: dataset validation, unit tests, public-safety scan, and markdown/link checks if available.
5. Define regression gates for deterministic scorer thresholds, calibrated judge thresholds, citation/no-private-source gates, confidence interval movement, and cost/latency budgets.
6. Write `docs/orchestration.md`, `docs/regression-gates.md`, and `docs/cost-controls.md`.

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
- `.github/workflows/validate.yml` or equivalent placeholder workflow
- `docs/regression-gates.md`
- `docs/cost-controls.md`
- `scripts/check_regression_gate.py`

### Common failure modes

- Creating one giant script with no job boundaries.
- Failing to distinguish candidate generation from scoring.
- Storing reports without the manifest needed to reproduce them.
- Losing managed-job IDs, so you cannot fetch the result artifacts you already paid for.
- Using Step Functions to rebuild comparison/reporting that Bedrock already provides for the selected evaluation path.

### Additional CI/CD validation checks

- CI fails on invalid datasets.
- CI fails on unsafe public examples.
- Regression gates are documented with rationale.
- Cost controls separate experiment budget from any production monitoring path.
- Monitoring tracks refusal rate, unsupported-question rate, citation failures, evidence-strength calibration failures, rate-limit decisions, latency, token usage, and cost; raw model I/O remains in lab S3 invocation logs.
- Every run records a per-run cost estimate, Service Quotas checks, maximum prompt count, maximum candidate/config count, maximum repeated-run count, and required approval state before submitting managed jobs.

### Stretch goals

- Add a static report generator.
- Add Athena table definitions for S3 result layout.
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
| Run complex programmatic evals | Inspect AI on SageMaker/ECS/Batch | Eval logic is code, not only judge prompts |
| Validate data and run lightweight scoring | Local CLI first; tiny Lambda only for small code-based evaluators or event glue | Fast schema checks and deterministic scoring without turning Lambda into an eval runtime |
| Coordinate managed and custom work | Bedrock-native workflows first, Step Functions when preflight/CI/CD/cross-service glue is needed | Use managed comparison/reporting where supported; add explicit state, retries, failure handling, and auditability around it |
| Query historical results | S3 + Glue/Athena | Cheap evidence lake pattern |
| Block regressions in development | CI/CD regression gates | Converts evals into shipping discipline |

> The managed Bedrock rows still leave you owning preflight, dataset/trace prep, versioning, validation, judge calibration, and scenario-specific interpretation. Use native reports and comparison first; custom summarization is for unsupported views or cross-lane evidence.

## What Not to Overclaim

Do not claim:

- “Bedrock Evaluations is the whole harness.” It is a managed evaluation component.
- “BYOI evaluates any live app automatically.” Bedrock model-eval BYOI means you provide `modelResponses` in the expected schema and Bedrock skips model invocation; live app evaluation belongs in a custom capture pipeline feeding supported inputs.
- “LLM-as-judge is ground truth.” It is a judge with measurable error.
- “Synthetic tests prove production safety.” They prove behavior on synthetic tests.
- “The candidate agent is safe because it has evals.” Evals are scoped evidence, not a guarantee.
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
- SageMaker Inspect AI container: <https://docs.aws.amazon.com/nova/latest/userguide/nova-eval-inspect-ai-container.html>

These pages are the source of truth for schemas, field names, metric lists, job constraints, and evaluation modes. This plan paraphrases them to stay readable; where the two disagree, follow the docs, and assume AWS has shipped changes since this was written.

## Final Standard

The final artifact should make one thing obvious: you can build AWS eval infrastructure with disciplined engineering. Not “I prompted a judge model once.” Not “I made a dashboard.” A real learning harness: versioned inputs, scoped claims, repeatable deterministic steps, calibrated judges, measured variance, deterministic checks, traceable outputs, quota-aware cost controls, and public-safe receipts.
