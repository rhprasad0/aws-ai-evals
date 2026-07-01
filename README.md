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

## Current status

**Week 5 is complete.** The repo now has the local eval contract layer, a minimal profile-only specimen path, blind response capture, and a browser/headless workflow for human pass/fail labels:

- `profile.md` as the sole public-safe candidate evidence source;
- readable JSON Schemas for eval examples, captured responses, and human labels;
- valid and invalid schema fixtures;
- `datasets/synthetic/recruiter-evidence-qa.jsonl` as the first recruiter-evidence synthetic dataset;
- `scripts/validate_dataset.py` as the canonical schema/dataset validator;
- `scripts/public_safety_scan.py` as the public-artifact safety scanner;
- a small browser workbench for reviewing/editing the synthetic dataset;
- a profile-only specimen prompt/response interface;
- a stubbed local runner plus opt-in Bedrock/Nova smoke mode;
- blind prompt mode so eval metadata and expected-answer notes are not taped to the model's forehead;
- harder recruiter, prompt-injection, and hallucination-bait rows for stress-testing the profile-only boundary;
- reviewed captured-response fixtures for the accepted 3-row live smoke;
- reviewed human-label fixtures for the accepted 3-row live smoke;
- a reviewed 48-row blind label fixture with 45 human passes, 3 human fails, and all 3 failures tagged `off_contract`;
- `scripts/eval_harness.py` for joining examples, captured responses, and labels by `exampleId`;
- text, JSON, and Markdown summaries for local harness results;
- `scripts/label_workbench.py` for reviewing captured responses, saving draft labels, and exporting schema-valid complete label sets;
- `scripts/run_judge_smoke.py` plus `schemas/judge-output.schema.json` for the first binary judge-calibration smoke against human labels;
- GitHub Actions CI running validation, safety scanning, tests, and whitespace checks.

Week 6 is now underway: Claude Sonnet 4.6 via the US Bedrock inference profile has produced the first binary judge smoke against the 48 reviewed labels. The first run agreed with Ryan on 47/48 rows, with one false fail and zero false passes; that is a calibration receipt, not a regression gate yet.

## 12-week schedule

| Status | Week | Focus | Outcome |
| --- | --- | --- | --- |
| ✅ Complete — foundation poured | 1 | Eval/product contract and repo boundaries | Simplified profile-only contract, architecture notes, public/private source rules, and explicit no-production-AI overclaim boundary. |
| ✅ Complete — contracts locked | 2 | Dataset contracts and schema validators | `profile.md`, schemas, fixtures, first synthetic dataset, browser workbench, validator, public-safety scanner, and CI. The eval runway now has guardrails instead of vibes in a trench coat. |
| ✅ Complete — specimen captured | 3 | Minimal profile-only specimen and trace contract | Profile-only prompt seam, stub runner, opt-in Nova smoke mode, normalized captured responses, reviewed smoke fixtures, and no deployment/RAG/judge-rubric sprawl. |
| ✅ Complete — clipboard online | 4 | Local harness and deterministic gates | Local harness joins examples, captured responses, and human labels; validates mechanical gates; reports text/JSON/Markdown summaries without pretending unlabeled rows prove model quality. |
| ✅ Complete — review desk | 5 | Human labeling workflow | Browser/headless labeling workflow, blind captures, harder stress prompts, and a reviewed 48-row human-label fixture: 45 pass, 3 fail, all `off_contract`. |
| 🧪 In progress — tiny robot grader | 6 | Binary judge calibration | Claude Sonnet 4.6 predicts pass/fail against the human labels, reports agreement/false passes/false fails/tag drift, and keeps generated judge output separate from source-of-truth labels. |
| ⏳ Queued | 7 | Bedrock model evals | Bedrock model-eval/BYOI jobs after local contracts and labels are solid; managed reports treated as evidence, not the whole harness. |
| ⏳ Queued | 8 | Bedrock RAG evals | Separate retrieval quality from answer quality; validate corpus support, citations, unsupported behavior, and distractors. |
| ⏳ Queued | 9 | Observability and lab trace capture | Bedrock invocation logging for lab/eval runs, app-level traces, S3 layout, retention, and public-safe normalized exports. |
| ⏳ Queued | 10 | Inspect AI and custom programmatic evals | Inspect tasks or equivalent custom runners for checks that do not fit managed Bedrock evals. |
| ⏳ Queued | 11 | Orchestration, CI, and regression gates | Local workflow simulation, manifests, run-result schema, CI checks, cost controls, and calibrated regression thresholds. |
| ⏳ Queued | 12 | Capstone reference architecture | Public-safe package with schemas, datasets, validators, scorers, Bedrock/RAG/Inspect adapters, runbooks, reports, and limitations. |

## Guardrails

- **Deployment/polish waits.** The chatbot should stay boring until evals can judge it usefully.
- **AgentCore/tool-use evals are out of scope for this iteration.** Future Calendar, Slack, or write-action tools can get a separate plan later.
- **Public answers need public/project-safe sources.** No Honcho, Graphiti, private notes, transcripts, private repos, raw traces, or provider responses unless explicitly curated into public-safe docs.
- **Raw lab evidence stays out of git.** Raw Bedrock invocation logs and traces belong in same-Region lab S3 with retention and access boundaries.
- **Synthetic is not automatically safe.** Prompt-injection and abuse examples should use inert canaries, not copy-pasteable attack payloads.
- **LLM judges are measurements, not truth.** Human labels, deterministic gates, repeated runs, and variance analysis keep the judges honest.
- **No magic production claims.** Passing evals are scoped evidence, not a safety certificate or universal correctness proof.
