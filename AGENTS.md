# AGENTS.md

This repository is public-facing by default. Treat every committed file as billboard-safe.

## Safety rules

Never commit:
- AWS credentials, API keys, OAuth tokens, cookies, or session material
- real account IDs, private ARNs, private bucket names, private endpoints, or local IPs
- real personal data, transcripts, Slack IDs, private paths, or raw logs
- `.env` values, credential caches, generated provider responses, or unredacted traces

Use:
- fictional account IDs such as `111122223333`
- example buckets such as `s3://example-eval-bucket/...`
- `example.com` addresses and synthetic data
- redacted or broken token-shaped examples such as `A[K]IA...`

## Project intent

Build a hands-on AWS AI evals learning path focused on reproducible harness engineering:
model evals, RAG evals, agent/tool evals, BYOI dataset adapters, judge validation,
custom scorers, observability, orchestration, cost controls, and public-safe evidence.

## Agent rules

- Keep public claims technically grounded and scoped.
- Prefer checkable artifacts over vibes.
- Do not add real AWS resource identifiers or local machine details.
- Do not commit scratch prompts, local logs, or generated raw eval outputs.
- If using coding agents, they may edit docs but Hermes owns final verification and commit.
