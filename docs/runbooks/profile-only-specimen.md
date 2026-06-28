# Profile-Only Specimen Interface

This runbook covers the Week 3 specimen boundary: one eval-example row plus `profile.md` becomes a prompt wrapper and a captured-response record.

## What this is

The specimen interface is the smallest contract surface for the future chatbot runner. It defines:

- the dataset row input (`exampleId`, `question`, and behavior metadata);
- `profile.md` as the only evidence source;
- profile delimiters in the prompt wrapper;
- the minimal model response JSON shape: `answer` plus optional `responseKind`;
- captured-response records matching `schemas/captured-response.schema.json`.

## What this is not

This interface does not:

- call Bedrock or any other model;
- deploy a chatbot;
- add RAG, retrieval, citations, source labels, evidence-strength labels, judge rubrics, or managed Bedrock jobs;
- treat `responseKind` as a human label;
- write raw provider responses or traces.

## Inspect a prompt

From the repo root:

```bash
python3 scripts/profile_specimen.py \
  --example-id prod-ai-direct-001 \
  --prompt
```

The prompt contains explicit `profile.md` delimiters:

```text
<<<PROFILE_MD_START>>>
...
<<<PROFILE_MD_END>>>
```

The model-facing response contract is intentionally tiny:

```json
{"answer":"short public-safe answer","responseKind":"answer|caveat|not_supported|refusal"}
```

## Emit a stub captured response

```bash
python3 scripts/profile_specimen.py \
  --example-id prod-ai-direct-001 \
  --run-id local-stub-001
```

This prints a schema-shaped captured-response JSON object using `modelId: stub-local`. It is a fixture/debug path only; it does not claim model behavior.

## Run a local stub capture

Use the runner to iterate over selected dataset rows and write captured-response JSONL under ignored `build/` output:

```bash
python3 scripts/run_profile_specimen.py \
  --production-probes \
  --limit 3
```

Expected success shape:

```text
OK: wrote 3 captured response(s) to build/captured-responses/local-stub-YYYYMMDDHHMMSS.jsonl
OK: validated against schemas/captured-response.schema.json
```

Useful targeting options:

```bash
python3 scripts/run_profile_specimen.py --example-id prod-ai-direct-001
python3 scripts/run_profile_specimen.py --example-id prod-ai-direct-001 --example-id off-topic-canary-001
python3 scripts/run_profile_specimen.py --production-probes --limit 2 --output /tmp/profile-specimen.jsonl
```

Stub mode proves row selection, captured-response wrapping, JSONL writing, and schema validation before live model integration.

## Run a live Bedrock smoke capture

Live mode is opt-in and writes only normalized captured-response JSONL. It does not save raw Bedrock request/response envelopes, traces, request IDs, or provider metadata.

```bash
python3 scripts/run_profile_specimen.py \
  --mode bedrock \
  --model-id us.amazon.nova-2-lite-v1:0 \
  --region us-east-1 \
  --example-id prod-ai-direct-001 \
  --example-id unsupported-cert-001 \
  --example-id off-topic-canary-001 \
  --run-id local-bedrock-smoke \
  --output /tmp/profile-specimen-bedrock-smoke.jsonl
```

Validate the generated JSONL:

```bash
python3 scripts/validate_dataset.py --jsonl captured-response /tmp/profile-specimen-bedrock-smoke.jsonl
```

Keep these smoke sets tiny until human labeling exists. Do not commit generated live outputs.

## Validate the interface

```bash
python3 tests/test_profile_specimen.py
python3 scripts/validate_dataset.py --json captured-response tests/fixtures/schemas/captured-response.valid.json
```

For full local CI parity, run:

```bash
python3 scripts/validate_dataset.py
python3 scripts/public_safety_scan.py
python3 tests/test_schema_fixtures.py
python3 tests/test_validate_dataset.py
python3 tests/test_public_safety_scan.py
python3 tests/test_profile_specimen.py
python3 tests/test_run_profile_specimen.py
python3 tests/test_dataset_workbench.py
git diff --check
```

## Next implementation slice

The next Week 3 slice should inspect a tiny live smoke output manually and decide whether the prompt needs tightening before expanding rows or adding labels.
