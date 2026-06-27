# AGENTS.md

This repository is public-facing by default. Treat every committed file as billboard-safe.

## Safety rules

Never commit:

- AWS credentials, API keys, OAuth tokens, cookies, or session material
- `.env` values, credential caches, generated provider responses, or unredacted traces

Use:

- placeholders such as `<AWS_ACCOUNT_ID>`


## Agent rules

- Do not commit scratch prompts, local logs, generated raw eval outputs, or provider responses.
- If a task requires choosing an evaluation target, schema boundary, labeling workflow, success criterion, AWS service path, or product direction, ask Ryan first.
