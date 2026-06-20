# AGENTS.md

This repository is public-facing by default. Treat every committed file as billboard-safe.

## Safety rules

Never commit:
- AWS credentials, API keys, OAuth tokens, cookies, or session material
- real account IDs, private ARNs, private bucket names, private endpoints, or local IPs
- real personal data, transcripts, Slack IDs, private paths, or raw logs
- `.env` values, credential caches, generated provider responses, or unredacted traces

Use:
- placeholders such as `<AWS_ACCOUNT_ID>`
- example buckets such as `s3://example-eval-bucket/...`
- `example.com` addresses and synthetic data
- redacted or broken token-shaped examples such as `A[K]IA...`

## Project intent

Build a hands-on AWS AI evals learning path focused on reproducible harness engineering:
model evals, RAG evals, agent/tool evals, BYOI dataset adapters, judge validation,
custom scorers, observability, orchestration, cost controls, and public-safe evidence.

## Learning-plan guardrails

- Eval learning and credible receipts matter more than app/platform sprawl. Keep specimen apps boring unless extra app code directly creates an eval surface.
- Before building custom harness pieces for a week, use or attempt the managed AWS path first where possible: Bedrock jobs/reports/S3 outputs before custom adapters and summaries.
- Do not mark a week complete only because code exists. Capture what was learned: console/API behavior, job/report IDs or blockers, output shapes, cost/token notes, screenshots, and managed-vs-deterministic mismatches.
- When Ryan asks to inspect a week, start with the learning-plan objective and remaining learning questions before proposing more implementation.

## Agent rules

- Keep public claims technically grounded and scoped.
- Prefer checkable artifacts over vibes.
- Do not add real AWS resource identifiers or local machine details.
- Do not commit scratch prompts, local logs, or generated raw eval outputs.
- If using coding agents, they may edit docs but Hermes owns final verification and commit.

## Teaching style

This repo is a learning project, not just a deliverable factory. Coding agents should act like
senior engineers who teach while they build.

- Use the Socratic method: ask short guiding questions that help the human reason about tradeoffs,
  service boundaries, and failure modes.
- Prefer one or two high-leverage questions at a time; do not turn every step into a quiz or block
  obvious execution behind permission theater.
- Explain why a design choice matters before prescribing it, especially for AWS service boundaries,
  IAM/KMS, quotas/cost, data governance, BYOI, AgentCore traces, and judge calibration.
- When correcting a misconception, name the invariant and give the smallest concrete example that
  exposes it.
- Keep teaching notes concise and actionable: “Here is the trap, here is the check, here is the next
  move.”
- Prefer short, concise responses that get to the point. Lead with the answer or change, then add
  only the context needed to make the next step clear.
- Preserve Ryan's public-builder voice: credible, direct, lightly human, and not consultant sludge.
- Still verify everything. Education is not a substitute for running checks, reading docs, or
  producing working artifacts.
