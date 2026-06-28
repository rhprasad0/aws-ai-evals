# Local Eval Harness

Week 4 starts here: join the dataset, captured responses, and human labels with boring mechanical checks.

## What this is

`scripts/eval_harness.py` validates and summarizes local eval artifacts:

- eval-example rows from `datasets/synthetic/recruiter-evidence-qa.jsonl`;
- captured responses from `tests/fixtures/captured-responses/live-smoke-reviewed.jsonl`;
- human labels from `tests/fixtures/human-labels/live-smoke-reviewed.jsonl`.

It joins rows by `exampleId`, checks label `runId` against the matching captured response, and prints counts for missing responses, missing labels, pass/fail outcomes, failure tags, and production-AI probes.

## What this is not

The harness does not score answer quality by itself. Pass/fail comes from `human-label/v1` rows only. It does not add judge rubrics, citation scoring, evidence-strength scoring, source ledgers, Bedrock jobs, deployment, or managed eval reports.

## Run the default reviewed-smoke summary

```bash
python3 scripts/eval_harness.py
```

Expected shape:

```text
Local eval harness summary
==========================
examples: 18
captured responses: 3
human labels: 3
labeled responses: 3
pass: 3
fail: 0
failure tags: none
production AI probes: total=... response=1 label=1 pass=1 fail=0
missing responses: 15
missing labels: 15
orphan responses: 0
orphan labels: 0
```

The missing counts are expected right now: only the reviewed 3-row live smoke has captured responses and human labels.

## JSON output

```bash
python3 scripts/eval_harness.py --json
```

Use this for tests or future report generation.

## Custom files

```bash
python3 scripts/eval_harness.py \
  --examples datasets/synthetic/recruiter-evidence-qa.jsonl \
  --responses tests/fixtures/captured-responses/live-smoke-reviewed.jsonl \
  --labels tests/fixtures/human-labels/live-smoke-reviewed.jsonl
```

## Local verification

```bash
python3 scripts/eval_harness.py
python3 scripts/eval_harness.py --json
python3 tests/test_eval_harness.py
python3 scripts/validate_dataset.py --jsonl human-label tests/fixtures/human-labels/live-smoke-reviewed.jsonl
```

Keep generated or broader run outputs under ignored `build/` or `/tmp` unless Ryan explicitly promotes a reviewed, public-safe fixture.
