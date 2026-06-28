# Synthetic Dataset Workbench

This runbook covers the local browser workbench for reviewing and editing `datasets/synthetic/recruiter-evidence-qa.jsonl`.

## What it is for

Use the workbench to inspect and edit synthetic recruiter-evidence eval rows with schema validation before save.

It supports:

- browsing every JSONL row;
- filtering by request class, expected behavior, source support, production-AI probe, and free text;
- editing row fields through form controls or raw JSON;
- viewing schema-derived helper copy for enum/dropdown values;
- optionally viewing `profile.md` as read-only context;
- saving the dataset atomically only after validation passes.

## What it is not for

The workbench does not:

- call models or generate answers;
- label captured model responses;
- manage raw traces, provider responses, or lab outputs;
- edit `profile.md`;
- run AWS, Bedrock, Inspect, or hosted eval jobs.

## Run it

From the repo root:

```bash
python3 scripts/dataset_workbench.py \
  datasets/synthetic/recruiter-evidence-qa.jsonl \
  --schema schemas/eval-example.schema.json \
  --profile profile.md \
  --port 8765
```

Then open:

```text
http://127.0.0.1:8765/
```

For a headless or remote environment, bind explicitly and tunnel or expose only through a trusted path:

```bash
python3 scripts/dataset_workbench.py \
  datasets/synthetic/recruiter-evidence-qa.jsonl \
  --schema schemas/eval-example.schema.json \
  --profile profile.md \
  --host 0.0.0.0 \
  --port 8765
```

## Validate without serving the UI

```bash
python3 scripts/dataset_workbench.py \
  datasets/synthetic/recruiter-evidence-qa.jsonl \
  --schema schemas/eval-example.schema.json \
  --check
```

Expected success shape:

```text
OK: 18 rows validated
```

## Save behavior

- Existing `exampleId` values are read-only in the UI.
- Edits update server memory first.
- `Save dataset changes` validates the full dataset before writing.
- Invalid JSON, schema errors, duplicate IDs, and missing required fields block save.
- Writes are atomic and preserve one compact JSON object per line.
- If the dataset changed on disk after the workbench loaded it, save fails closed and asks for reload.

## Public-safety reminder

Commit only synthetic rows, schemas, scripts, tests, and docs. Do not commit raw provider responses, private notes, local memory exports, account identifiers, credentials, `.env` values, or unredacted traces.
