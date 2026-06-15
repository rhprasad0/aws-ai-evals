# AWS AI Evals

Public learning repo for building an AWS-native AI evaluation harness — the kind of thing recruiters can inspect instead of taking “I know evals” on faith.

This is a hands-on AI Engineering artifact: I am turning a 12-week plan into a public-safe reference architecture for evaluating LLM apps on AWS. The focus is not a toy benchmark or a pretty dashboard. It is the plumbing around trustworthy evals: dataset contracts, Bedrock model/RAG evaluations, AgentCore agent/tool evaluations, deterministic scorers, judge calibration, run manifests, orchestration, observability, cost controls, and evidence reports.

Start here:

- [`docs/aws-ai-evals-learning-plan.md`](docs/aws-ai-evals-learning-plan.md) — 12-week roadmap and source ledger
- [`AGENTS.md`](AGENTS.md) — repo rules for public safety, teaching style, and coding-agent behavior

## For recruiters

This repo is meant to show how I work as an AI systems builder:

- I turn fuzzy “evaluate the AI” goals into concrete, testable harness architecture.
- I separate managed AWS evaluation services from the glue code, governance, and reporting the builder still owns.
- I treat LLM-as-judge as a measured instrument: calibrated, repeated, compared to human labels, and never mistaken for ground truth.
- I front-load security and cost: IAM, KMS, model access, quotas, data residency, retention, and public-safe artifacts.
- I document the traps: BYOI boundaries, stochastic reproducibility limits, AgentCore trace formats, Lambda misuse, and overclaiming production readiness.

Translation: this is not “prompted Claude and vibe-checked it.” This is eval infrastructure with adult supervision and receipts.

## What this is

A public-safe AWS AI evals learning harness, built in stages:

- Bedrock model evaluations and model-as-judge jobs
- Bedrock RAG retrieval and retrieve-and-generate evaluations
- Bedrock AgentCore agent/tool evaluations with OpenTelemetry/OpenInference-compatible traces
- Inspect AI custom evals on AWS
- BYOI dataset adapters and validators
- deterministic scorers and judge calibration
- run manifests, reports, orchestration, CI gates, observability, and cost/security controls

## Progress chart

Current phase: **planning and repo contracts**. The roadmap is intentionally documentation-first, then code/infrastructure.

| Week | Focus | Status | Progress |
|---:|---|---|---|
| 1 | Evaluability design, security envelope, repo contracts | In progress | ███░░ 60% |
| 2 | Dataset contracts and schema validators | Not started | ░░░░░ 0% |
| 3 | Trace capture and observability baseline | Not started | ░░░░░ 0% |
| 4 | Bedrock model evaluations | Not started | ░░░░░ 0% |
| 5 | Custom metrics and judge rubrics | Not started | ░░░░░ 0% |
| 6 | Bedrock RAG evaluations | Not started | ░░░░░ 0% |
| 7 | Deterministic scorers and small event glue | Not started | ░░░░░ 0% |
| 8 | AgentCore agent/tool evaluations | Not started | ░░░░░ 0% |
| 9 | Inspect AI on AWS | Not started | ░░░░░ 0% |
| 10 | Orchestration, manifests, repeatable evidence | Not started | ░░░░░ 0% |
| 11 | CI/CD, regression gates, monitoring, cost controls | Not started | ░░░░░ 0% |
| 12 | Capstone reference architecture package | Not started | ░░░░░ 0% |

```mermaid
gantt
    title AWS AI Evals Learning Plan Progress
    dateFormat  YYYY-MM-DD
    axisFormat  Week %W
    section Foundations
    Learning plan revised and AWS service boundaries corrected :done, plan, 2026-06-15, 1d
    Repo public-safety and agent rules updated              :active, agents, 2026-06-15, 1d
    section Roadmap
    Week 1: evaluability + security envelope               :active, w1, 2026-06-16, 7d
    Week 2: dataset contracts + validators                 :w2, after w1, 7d
    Week 3: traces + observability                         :w3, after w2, 7d
    Week 4: Bedrock model evals                            :w4, after w3, 7d
    Week 5: judge rubrics + calibration                    :w5, after w4, 7d
    Week 6: Bedrock RAG evals                              :w6, after w5, 7d
    Week 7: deterministic scorers                          :w7, after w6, 7d
    Week 8: AgentCore evals                                :w8, after w7, 7d
    Week 9: Inspect AI on AWS                              :w9, after w8, 7d
    Week 10: orchestration + manifests                     :w10, after w9, 7d
    Week 11: CI/CD + monitoring + cost controls            :w11, after w10, 7d
    Week 12: capstone reference architecture               :w12, after w11, 7d
```

## Scope, honestly

This is a learning artifact, not a production eval service. Managed Bedrock and AgentCore evaluations are major components, but the harness is the part around them: dataset contracts, validators, security preflight, manifests, deterministic checks, calibrated judges, reporting, and public-safe receipts.

BYOI means different things in different AWS paths. For Bedrock model-eval BYOI, this repo treats it as supplied `modelResponses` in AWS's expected dataset shape. Live app evaluation belongs in AgentCore-supported flows or a custom capture pipeline that feeds supported inputs.

Everything here uses synthetic data and placeholders. No credentials, live AWS account details, private traces, real customer/user data, or working attack payloads belong in this repo. The safety and prompt-injection lanes use inert canaries, not copy-pasteable exploit recipes.
