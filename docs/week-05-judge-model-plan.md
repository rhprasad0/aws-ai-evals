# Week 5 Judge Model Plan

Week 5 measures judge quality, not just candidate-answer quality. Use multiple evaluator models deliberately so judge variance and judge-family bias are visible.

## Judge lineup

| Role | Evaluator model/profile | Why |
|---|---|---|
| Target independent judge | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Strong independent judge for nuanced rubric scoring once Anthropic model access/use-case details are approved in the AWS account. |
| Current runnable custom-metric judge | `us.amazon.nova-pro-v1:0` | Supported for Bedrock custom metrics and available in the current account; use this for the first real Week 5 custom-metric run. |
| Not supported for custom metrics | `us.anthropic.claude-sonnet-4-6` | Available as an inference profile, but Bedrock custom-metric evaluator validation rejects it today. |
| Control/baseline | `us.amazon.nova-2-lite-v1:0` | Week 4 plumbing baseline; keep for continuity, not as the serious calibration judge. |

## Run rule

For each rubric and dataset slice:

1. Run the same BYOI prompt set at least 3 times with the primary judge.
2. Run the same prompt set at least once with the comparison judge.
3. Join generated judge outputs to `datasets/synthetic/human-labels.jsonl` by `example_id` and `rubric_id`.
4. Report judge-vs-human agreement, repeated-run variance, confusion matrix, and high-variance cases.

No judge score becomes a regression gate until it clears the documented human-label agreement bar and repeated-run variance is low enough for that rubric.

## Human-label workflow

The first 105 `datasets/synthetic/human-labels.jsonl` rows were scaffold labels, not final calibration truth. They have been archived locally and the tracked label file is intentionally empty until the next manual labeling pass is complete.

Use the local workbench instead of hand-writing JSONL:

```bash
python3 scripts/human_label_workbench.py clear --labels datasets/synthetic/human-labels.jsonl --archive-dir build/human-labeling
python3 scripts/human_label_workbench.py gui --dataset datasets/synthetic/recruiter-evidence-qa.jsonl --labels datasets/synthetic/human-labels.jsonl
python3 scripts/human_label_workbench.py validate --dataset datasets/synthetic/recruiter-evidence-qa.jsonl --labels datasets/synthetic/human-labels.jsonl
```

The GUI depends on Tkinter. If `python3` reports `No module named 'tkinter'`, a venv will not fix it because Tkinter is an OS/Python-build extension; install the system package first on Ubuntu/Debian with `sudo apt-get install python3-tk`, then rerun the same command.

When working over SSH without X forwarding, use the browser workbench instead:

```bash
python3 scripts/human_label_web_workbench.py --host 0.0.0.0 --port 8765 --dataset datasets/synthetic/recruiter-evidence-qa.jsonl --labels datasets/synthetic/human-labels.jsonl
```

Then open `http://<machine-hostname-or-ip>:8765/` from a browser that can reach the machine. Bind to `127.0.0.1` instead if you are using SSH port forwarding.

Partial work is saved with the **Save draft** button to ignored local state at `build/human-labeling/draft-label-state.json`; both the Tkinter and browser workbenches reload that draft on startup. **Export completed labels** is stricter: it writes `datasets/synthetic/human-labels.jsonl` only when every example/rubric slot is complete and schema-valid.

The GUI uses the repo's direct `0`/`1`/`2` human-label scale: `0 = fail`, `1 = partial`, and `2 = pass`. Bedrock managed/built-in scores may appear normalized as floats such as `0.0`, `0.5`, `0.75`, or `1.0`; keep those visible as judge output and do not silently treat them as human labels.

Do not treat a Week 5 calibration report as meaningful until the label file validates with one complete row for every recruiter-evidence example and rubric.

## Bedrock job template

Use `infra/templates/bedrock-custom-metric-eval-job.json` for the first custom-metric run. It embeds the five Week 5 custom metric definitions, references the BYOI dataset through public-safe S3 placeholders, and sets the custom-metric evaluator to `us.amazon.nova-pro-v1:0`, which is currently runnable in the AWS account.

For a Sonnet comparison run after Anthropic access is approved, copy the template and change only `evaluationConfig.automated.customMetricConfig.evaluatorModelConfig.bedrockEvaluatorModels[0].modelIdentifier` to `us.anthropic.claude-sonnet-4-5-20250929-v1:0`; keep the dataset, metric definitions, and BYOI model identifier unchanged so the comparison isolates judge-model behavior.

## Terraform stance

Do not Terraform individual evaluation jobs. Terraform only the reusable IAM/S3/KMS runway. If the Bedrock eval role needs a different judge model, pass the judge model/profile variables during Terraform plan/apply and record the selected evaluator in the run manifest.

## Public-safe receipt

Commit only public-safe summaries: model/profile IDs, aggregate scores, agreement/variance tables, and sanitized screenshots. Keep raw Bedrock outputs, S3 paths with real bucket names, job ARNs, and generated judge records in scratch/private storage unless explicitly scrubbed.
