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

## Reset state

This repo has been intentionally reset after an initial AWS AI evals learning spike accumulated too much schema and evaluation-design debt.

Until Ryan defines the next direction, agents must treat this repo as a minimal starting point. Do not infer or revive the previous app specimen, eval schema, AWS service path, rubric set, dataset shape, weekly roadmap, Terraform stack, or chatbot assumptions from deleted history.

## Agent rules

- Keep public claims technically grounded and scoped.
- Prefer checkable artifacts over vibes.
- Do not add real AWS resource identifiers or local machine details.
- Do not commit scratch prompts, local logs, generated raw eval outputs, or provider responses.
- If Ryan gives a clear narrow task, execute it and verify it.
- If a task requires choosing an evaluation target, schema boundary, labeling workflow, success criterion, AWS service path, or product direction, ask Ryan first.
- Preserve Ryan's public-builder voice: credible, direct, lightly human, and not consultant sludge.
