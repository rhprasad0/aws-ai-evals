# AWS AI Evals

> Building a recruiter-facing evidence chatbot, then forcing it to survive an eval harness. No vibes-only victory laps.

Public learning repo for building an AWS-native AI evaluation harness around a real production experiment: the **ryanprasad.ai candidate evidence chatbot**.

The live app is a public chatbot that answers recruiter-style evidence questions about Ryan's public GitHub projects with citations — e.g. “Where does Ryan show container orchestration?” The learning goal is to build the AWS eval harness around that real behavior instead of evaluating a toy demo in a vacuum.

```text
evidence chatbot → traces → datasets → Bedrock/RAG evals → deterministic checks → public-safe receipts
```

Start here:

- [`docs/aws-ai-evals-learning-plan.md`](docs/aws-ai-evals-learning-plan.md) — 12-week roadmap, production experiment, and source ledger
- [`docs/ryanprasad-ai-chatbot.md`](docs/ryanprasad-ai-chatbot.md) — V1 candidate evidence chatbot spec
- [`docs/dataset-contracts.md`](docs/dataset-contracts.md) — Week 2 schemas, validator, and eval-lane contract map
- [`content/profile.md`](content/profile.md) — canonical public evidence source for the chatbot
- [`AGENTS.md`](AGENTS.md) — repo rules for public safety, teaching style, and coding-agent behavior

## The bet

A public AI evidence bot is only impressive if it can be inspected.

This repo treats `ryanprasad.ai` as the lab rat — useful, alive, slightly fancy — and builds the evaluation system around it. The point is not “chatbot exists.” The point is:

- can it answer recruiter questions from public evidence?
- can it say “I don't know” when the evidence is missing?
- can it cite the repo/profile sources that support the answer?
- can changes be gated by evals instead of vibes?

## For recruiters

This repo shows how I work as an AI systems builder:

- I turn a real product idea into evaluable system requirements.
- I separate managed AWS evaluation services from the glue code, governance, and reporting the builder still owns.
- I treat LLM-as-judge as a measured instrument: calibrated, repeated, compared to human labels, and never mistaken for ground truth.
- I front-load security and cost: IAM, KMS, model access, quotas, data residency, retention, and public-safe artifacts.
- I document the traps: BYOI boundaries, stochastic reproducibility limits, AgentCore trace formats, Lambda misuse, tool consent, and overclaiming production readiness.

Translation: this is not “prompted Claude and vibe-checked it.” This is a public AI agent plus eval infrastructure with adult supervision and receipts.

## Production experiment

The specimen is a public chatbot on `ryanprasad.ai`.

**Deployment receipt:** V1 is live on the lab domain and answering/refusing through the deployed UI.

![Deployment receipt: ryanprasad.ai candidate evidence chatbot live on chat.ryans-lab.click](docs/assets/chatbot-deployment-receipt-2026-06-16.png)

**Week 1 closeout receipt:** local gates passed for backend tests, frontend build, dataset/schema validation, deterministic citation/overclaim/refusal checks, Terraform validation, run-manifest validation, and public-safety scanning. Live backend smoke tests covered supported evidence, production-overclaim refusal, private-source refusal, and an inert prompt-injection canary.

It should:

- answer recruiter questions about Ryan's public GitHub projects from public/project-safe sources, with citations;
- map skills to concrete public evidence, starting with questions like “Where does Ryan show container orchestration?”;
- distinguish strong evidence, lab/project evidence, weak evidence, and unsupported claims;
- refuse or escalate unsupported, private, unsafe, or ambiguous requests.

RAG/project Q&A comes first because it is the main user value and the cleanest place to build citation-backed evidence. Calendar booking and Slack relay are deferred tool-use flows, not V1 scope.

## What this is

A public-safe AWS AI evals learning harness, built in stages:

| Layer | What it proves |
|---|---|
| Public/project RAG | Recruiter answers are grounded in inspectable sources, not résumé fan fiction |
| Citation checks | Every skill claim points to a public source label |
| Evidence calibration | The bot says when evidence is lab/project/WIP instead of puffing it up |
| Bedrock evaluations | Managed model/RAG scoring is used where AWS already provides it |
| Agent/tool evaluations | Optional Phase 2 tool trajectories are testable if Calendar/Slack return later |
| Deterministic scorers | Secrets, citations, schemas, unsupported claims, and limits get hard checks |
| CI/reporting | Changes produce public-safe receipts instead of “trust me bro” |

## Product boundaries

The useful invariant: the chatbot can explain Ryan's public evidence, but it cannot become a résumé fan-fiction machine.

- No private memory, private notes, transcripts, or private repo content in public answers unless explicitly curated into public-safe docs.
- No Calendar or Slack writes in V1.
- GitHub/project Q&A cites public sources and says “I don't know” when support is missing.
- Evidence strength is part of the answer: strong public artifact, lab/project artifact, WIP, weak support, or unsupported.

## Progress chart

Current phase: **Week 2 closed: dataset contracts, live deterministic capture, and BYOI export lane validated**. The roadmap is documentation-first, then code/infrastructure, with the `ryanprasad.ai` candidate agent as the live specimen from Week 1.

| Week | Focus | How the chatbot fits | Status | Progress |
|---:|---|---|---|---|
| 1 | 🧭 Evaluability design, security envelope, repo contracts | Define recruiter evidence questions, citation rules, data boundaries, IAM/secrets, threat model | ✅ Closed | 🟩🟩🟩🟩🟩 100% |
| 2 | 🧱 Dataset contracts and schema validators | Synthetic recruiter Q&A, skill-to-evidence labels, unsupported/private-info, and inert injection cases | ✅ Closed | 🟩🟩🟩🟩🟩 100% |
| 3 | 📡 Trace capture and observability baseline | Chat turns, source labels, evidence strength, refusals, latency, token/cost usage | ⏳ Not started | ⬜⬜⬜⬜⬜ 0% |
| 4 | ⚖️ Bedrock model evaluations | Evaluate answer quality and judge behavior for candidate-agent turns | ⏳ Not started | ⬜⬜⬜⬜⬜ 0% |
| 5 | 🧪 Custom metrics and judge rubrics | Calibrate rubrics for project answers, refusals, consent, and tool safety | ⏳ Not started | ⬜⬜⬜⬜⬜ 0% |
| 6 | 🔎 Bedrock RAG evaluations | Evaluate public GitHub/project retrieval and citation support | ⏳ Not started | ⬜⬜⬜⬜⬜ 0% |
| 7 | ✅ Deterministic scorers and small event glue | Check citations, no secrets, valid tool payloads, confirmation gates, rate limits | ⏳ Not started | ⬜⬜⬜⬜⬜ 0% |
| 8 | 🛠️ Agent/tool evaluations | Optional Phase 2: evaluate Calendar/Slack tool choice only if tools are added later | ⏳ Not started | ⬜⬜⬜⬜⬜ 0% |
| 9 | 🧰 Inspect AI on AWS | Replay candidate-agent scenarios and custom evals | ⏳ Not started | ⬜⬜⬜⬜⬜ 0% |
| 10 | 🔁 Orchestration, manifests, repeatable evidence | Run repeatable candidate-agent eval suites with versioned manifests | ⏳ Not started | ⬜⬜⬜⬜⬜ 0% |
| 11 | 🚦 CI/CD, regression gates, monitoring, cost controls | Gate risky chatbot changes and monitor drift/cost/failures | ⏳ Not started | ⬜⬜⬜⬜⬜ 0% |
| 12 | 📦 Capstone reference architecture package | Publish public-safe evidence packet for the live experiment | ⏳ Not started | ⬜⬜⬜⬜⬜ 0% |

```mermaid
gantt
    title ryanprasad.ai Candidate Agent + AWS AI Evals Progress
    dateFormat  YYYY-MM-DD
    axisFormat  Week %W
    section Foundations
    Learning plan revised and AWS service boundaries corrected :done, service-boundaries, 2026-06-15, 1d
    Repo public-safety and agent rules updated              :done, agent-rules, 2026-06-15, 1d
    Candidate-agent production experiment slotted into plan :active, candidate-agent-plan, 2026-06-15, 1d
    section Roadmap
    Week 1: evaluability + security envelope               :done, w1, 2026-06-16, 7d
    Week 2: datasets + tool contracts                      :w2, after w1, 7d
    Week 3: production traces + observability              :w3, after w2, 7d
    Week 4: Bedrock model evals                            :w4, after w3, 7d
    Week 5: judge rubrics + calibration                    :w5, after w4, 7d
    Week 6: Bedrock RAG evals                              :w6, after w5, 7d
    Week 7: deterministic scorers                          :w7, after w6, 7d
    Week 8: AgentCore tool evals                           :w8, after w7, 7d
    Week 9: Inspect AI on AWS                              :w9, after w8, 7d
    Week 10: orchestration + manifests                     :w10, after w9, 7d
    Week 11: CI/CD + monitoring + cost controls            :w11, after w10, 7d
    Week 12: public evidence packet                        :w12, after w11, 7d
```

## Scope, honestly

This is a learning artifact and live production experiment, not a production safety certificate. Managed Bedrock and AgentCore evaluations are major components, but the harness is the part around them: dataset contracts, validators, security preflight, manifests, deterministic checks, calibrated judges, reporting, and public-safe receipts.

BYOI means different things in different AWS paths. For Bedrock model-eval BYOI, this repo treats it as supplied `modelResponses` in AWS's expected dataset shape. Live app evaluation belongs in AgentCore-supported flows or a custom capture pipeline that feeds supported inputs.

Everything here uses synthetic data, placeholders, or explicitly public/project-safe sources. No credentials, live AWS account details, private traces, real visitor content, private calendar IDs, Slack destinations, or working attack payloads belong in this repo. The safety and prompt-injection lanes use inert canaries, not copy-pasteable exploit recipes.

## Current north star

Ship the smallest useful public evidence bot, then make every claim observable, testable, and boring. Boring is good. Boring means the résumé raccoon found the lid locked.
