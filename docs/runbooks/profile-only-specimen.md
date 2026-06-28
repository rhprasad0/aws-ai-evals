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
python3 tests/test_dataset_workbench.py
git diff --check
```

## Next implementation slice

The next Week 3 slice should add a local runner that iterates over a small dataset slice, calls either this stub path or a model adapter, writes captured-response JSONL, and validates the output against `schemas/captured-response.schema.json`.
