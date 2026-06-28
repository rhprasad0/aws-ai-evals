# Human Label Workbench

Week 5 starts here: review captured responses and export binary `human-label/v1` labels.

## Generate responses for all dataset rows

The context warning about `@file:datasets/synthetic/recruiter-evidence-qa.jsonl` can be ignored when working from the repo root; the tracked dataset exists at that path.

Run the live specimen over all 18 rows and keep the generated responses in ignored `build/` output:

```bash
python3 scripts/run_profile_specimen.py \
  --mode bedrock \
  --model-id us.amazon.nova-2-lite-v1:0 \
  --region us-east-1 \
  --run-id week5-all-rows \
  --output build/captured-responses/week5-all-rows.jsonl

python3 scripts/validate_dataset.py \
  --jsonl captured-response \
  build/captured-responses/week5-all-rows.jsonl
```

Do not commit the generated all-row response JSONL unless Ryan explicitly promotes a reviewed, public-safe fixture.

## Check workbench inputs

```bash
python3 scripts/label_workbench.py \
  --responses build/captured-responses/week5-all-rows.jsonl \
  --check
```

Expected right after generation:

```text
OK: 18 response row(s), 0 labeled, 18 unlabeled
```

## Launch the browser workbench

```bash
python3 scripts/label_workbench.py \
  --host 0.0.0.0 \
  --port 8766 \
  --responses build/captured-responses/week5-all-rows.jsonl \
  --draft build/labels/human-label-draft.json \
  --output build/labels/human-labels.jsonl
```

Open `http://<host>:8766/`.

The workbench shows:

- dataset row and expected behavior;
- captured response answer;
- read-only `profile.md` context;
- binary `pass` / `fail` controls;
- failure tags from `schemas/human-label.schema.json`;
- optional review notes.

`Save draft` writes partial progress to ignored `build/labels/human-label-draft.json`. `Export validated labels` writes complete schema-valid JSONL to ignored `build/labels/human-labels.jsonl`; export is blocked until every captured response has `pass` or `fail`.

## Validate exported labels

```bash
python3 scripts/validate_dataset.py \
  --jsonl human-label \
  build/labels/human-labels.jsonl

python3 scripts/eval_harness.py \
  --responses build/captured-responses/week5-all-rows.jsonl \
  --labels build/labels/human-labels.jsonl \
  --markdown
```

## Boundaries

- Pass/fail is human judgment, not `responseKind` automation.
- Failure tags are optional diagnosis, not separate rubric scores.
- Draft files and all-row live outputs stay ignored under `build/`.
- Commit only reviewed, public-safe fixtures or docs.
