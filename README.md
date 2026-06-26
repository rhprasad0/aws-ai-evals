# AWS AI Evals

This repo is the second-pass workspace for building an AWS-focused AI evaluation harness around a deliberately boring public candidate-evidence chatbot specimen.

The first attempt built a candidate-evidence chatbot and an AWS/Bedrock eval harness around it. That work was useful as a learning spike, but it moved too quickly: the schema design, labeling workflow, and eval shape accumulated too much cognitive debt. Rather than keep layering tools on a shaky contract, the repo was reset to a minimal starting point.

## Current direction

The next pass is **evals-first**:

- define the evaluation contract before polishing or deploying the chatbot;
- build schemas, synthetic datasets, validators, deterministic gates, and human-label workflow first;
- keep the chatbot as a minimal specimen until local evals can say useful things about citations, evidence strength, refusals, unsupported claims, and public/private source boundaries;
- use managed Bedrock model/RAG evals and Inspect/custom evals only after the local contract is checkable.

The retained roadmap is [`docs/aws-ai-evals-learning-plan.md`](docs/aws-ai-evals-learning-plan.md). Treat it as the planning reference for the second iteration, not permission to resurrect the removed implementation, datasets, rubrics, schemas, infrastructure, or chatbot assumptions.

## 12-week schedule

| Week | Focus | Outcome |
| --- | --- | --- |
| 1 | Eval/product contract, security envelope, repo contracts | Candidate-agent boundaries, public/private source rules, evidence taxonomy, refusal rules, run manifest, and security envelope. |
| 2 | Dataset contracts and schema validators | Schemas, synthetic prompts, citation/evidence labels, invalid fixtures, and validation tooling. |
| 3 | Minimal specimen and trace contract | Small local/stubbed chatbot specimen with normalized traces, citations, evidence strength, refusals, and structured errors. |
| 4 | Local harness and deterministic gates | Local eval run plus deterministic checks for schema validity, citations, source allowlists, refusals, and no-private-source rules. |
| 5 | Human labeling workflow | Browser/headless labeling workflow and pass/partial/fail labels before trusting judge scores. |
| 6 | Judge rubrics and calibration | Versioned rubrics, judge-vs-human agreement, variance, disagreement analysis, confusion matrix, and kappa. |
| 7 | Bedrock model evals | Bedrock model-eval/BYOI jobs after local contracts and labels are solid; managed reports treated as evidence, not the whole harness. |
| 8 | Bedrock RAG evals | Separate retrieval quality from answer quality; validate corpus support, citations, unsupported behavior, and distractors. |
| 9 | Observability and lab trace capture | Bedrock invocation logging for lab/eval runs, app-level traces, S3 layout, retention, and public-safe normalized exports. |
| 10 | Inspect AI and custom programmatic evals | Inspect tasks or equivalent custom runners for checks that do not fit managed Bedrock evals. |
| 11 | Orchestration, CI, and regression gates | Local workflow simulation, manifests, run-result schema, CI checks, cost controls, and calibrated regression thresholds. |
| 12 | Capstone reference architecture | Public-safe package with schemas, datasets, validators, scorers, Bedrock/RAG/Inspect adapters, runbooks, reports, and limitations. |

## Guardrails

- **Deployment/polish waits.** The chatbot should stay boring until evals can judge it usefully.
- **AgentCore/tool-use evals are out of scope for this iteration.** Future Calendar, Slack, or write-action tools can get a separate plan later.
- **Public answers need public/project-safe sources.** No Honcho, Graphiti, private notes, transcripts, private repos, raw traces, or provider responses unless explicitly curated into public-safe docs.
- **Raw lab evidence stays out of git.** Raw Bedrock invocation logs and traces belong in same-Region lab S3 with retention and access boundaries.
- **Synthetic is not automatically safe.** Prompt-injection and abuse examples should use inert canaries, not copy-pasteable attack payloads.
- **LLM judges are measurements, not truth.** Human labels, deterministic gates, repeated runs, and variance analysis keep the judges honest.
- **No magic production claims.** Passing evals are scoped evidence, not a safety certificate or universal correctness proof.
