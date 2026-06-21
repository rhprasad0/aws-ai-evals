# Dataset Contracts

Week 2 makes the eval data boring before the judges get expensive.

The chatbot is a small public-evidence specimen. These contracts define which JSON/JSONL shapes are allowed into deterministic checks, Bedrock model-eval BYOI exports, RAG-grounding compatibility exports, and run receipts.

## Contract hierarchy

1. **Native chatbot contract first** — `candidate-chat-turn.schema.json` and `chat-response.schema.json` describe the app behavior we actually own.
2. **Subcontracts second** — citations, evidence-strength labels, refusals, and run manifests keep labels closed and reproducible.
3. **AWS export lanes third** — Bedrock model-eval and RAG BYOI schemas are compatibility targets generated from native rows/captured answers, not the source of truth.

This matters because AWS schemas are strict and recruiter evidence is claim-sensitive. Bad citations, inflated evidence strength, private identifiers, and unsupported claims should fail locally before a Bedrock job or public bot gets near them.

## Validation command

Use the generalized validator for every JSON/JSONL fixture or export:

```bash
python3 scripts/validate_dataset.py \
  --schema schemas/recruiter-evidence-qa.schema.json \
  --input datasets/synthetic/recruiter-evidence-qa.jsonl
```

The validator:

- validates schemas with Draft 2020-12 rules;
- auto-detects `.jsonl` and validates line by line;
- reports line numbers and property paths;
- blocks public-safety leaks such as local home paths, Slack IDs, AWS keys/account IDs, token-shaped strings, private IPs/hostnames, non-example emails, and raw tracebacks.

## Schema map

| Schema | Lane | Purpose |
|---|---|---|
| `schemas/candidate-chat-turn.schema.json` | Native deterministic | Source-of-truth multi-turn eval row: messages, expected citations, required phrases, forbidden claims, expected evidence strength, reference answer, and expected outcome. |
| `schemas/recruiter-evidence-qa.schema.json` | Native deterministic / legacy | Current single-question recruiter fixture shape used by `datasets/synthetic/recruiter-evidence-qa.jsonl` and existing deterministic scoring. |
| `schemas/chat-response.schema.json` | Runtime response contract | Shape the live/local chatbot must return: `answer`, `citations`, `evidenceStrength`, and `unsupportedClaims`. |
| `schemas/citation-array.schema.json` | Subcontract | Closed allowlist of public source labels. Unknown citations fail instead of becoming résumé fan fiction. |
| `schemas/evidence-strength.schema.json` | Subcontract | Closed support labels such as `medium_high_lab_project`, `unsupported`, and `unsupported_private`. |
| `schemas/refusal-outcome.schema.json` | Subcontract | Refusal/escalation labels for unsupported public claims, private-source asks, prompt-injection canaries, rate limits, and human review. |
| `schemas/model-eval-prompt-dataset.schema.json` | Bedrock model eval | Prompt dataset shape when Bedrock invokes the selected model under test. |
| `schemas/bedrock-model-eval-byoi.schema.json` | Bedrock model eval BYOI | Prompt plus one supplied `modelResponses[]` item when the app/harness already generated the response and Bedrock should judge it. |
| `schemas/human-label.schema.json` | Judge calibration | Human-curated expected rubric labels for one source example and one rubric. These are the calibration baseline, not generated judge output. |
| `schemas/judge-output.schema.json` | Judge calibration | Machine-parseable LLM-as-judge output for one rubric/example/run/repetition. Human labels stay separate and join by `example_id` and `rubric_id`. |
| `schemas/rag-retrieve-generate-byoi.schema.json` | RAG grounding compatibility | Retrieve-and-generate BYOI shape for evaluating grounded answers, generated text, and retrieved passages from an external grounded-answer system. |
| `schemas/rag-retrieval-only-byoi.schema.json` | RAG grounding compatibility | Retrieve-only BYOI shape for evaluating retrieved passages without judging final generated text. |
| `schemas/run-manifest.schema.json` | Reproducibility | Run receipt for deterministic, live smoke, Bedrock model BYOI, or RAG BYOI eval lanes. |

## BYOI and RAG boundary

**BYOI means Bring Your Own Inference responses.** For Bedrock model-eval BYOI, this repo supplies `modelResponses`; Bedrock skips invoking the model under test and evaluates the response we provide.

The chatbot is not currently a Bedrock Knowledge Base or production vector-RAG stack. The RAG schemas exist because the bot's job is still grounded answering: answer from public source text, cite source labels, and avoid unsupported claims. Treat RAG BYOI here as **grounded-answer/citation compatibility**, not as a claim that V1 secretly shipped a full RAG platform.

No résumé inflation, even in JSON.

## Golden fixtures

Validator behavior is pinned by fixtures under `tests/fixtures/datasets/`:

```text
tests/fixtures/datasets/
  valid/
    recruiter-evidence-valid.jsonl
    run-manifest-valid.json
  invalid/
    bad-citation.jsonl
    bad-evidence-strength.jsonl
    duplicate-source-labels.jsonl
    extra-property.jsonl
    malformed-jsonl.jsonl
    missing-reference-response.jsonl
    private-email.jsonl
    private-home-path.jsonl
    slack-channel-id.jsonl
    unsupported-with-citation.jsonl
```

The invalid fixtures prove the validator catches both schema problems and public-safety leaks. If a schema change makes an invalid fixture pass, that is a contract regression unless the fixture and contract are intentionally revised together.

Run them with:

```bash
python3 -m unittest tests.test_validate_dataset -v
```

## Dataset rules

- Keep JSONL line-delimited: one object per line, no giant JSON arrays.
- Every stable row needs a schema/version field when the target schema requires one.
- Use synthetic data or explicitly public-safe project facts only.
- Record provenance before adding any non-synthetic fixture derived from public source material.
- Unsupported or private-source rows should have no expected citations.
- Material supported claims should have citations and reference responses.
- Prompt-injection fixtures should use inert canaries, not copy-pasteable exploit payloads.
- Store raw traces and Bedrock invocation logs outside public docs; commit only normalized, public-safe fixtures or receipts.

## How this feeds the next steps

1. Validate source datasets and fixtures locally.
2. Run local/live chatbot responses through `scripts/capture_candidate_chatbot_responses.py`; it validates each response against the backend response contract.
3. Score captured responses deterministically for citations, required content, forbidden claims, evidence strength, and refusal behavior.
4. Export captured answers into Bedrock model-eval BYOI rows. If deterministic scoring found failures, treat the BYOI file as judge-calibration input, not a clean regression batch.
5. For Week 5 calibration, validate human labels and judge outputs, then run `scripts/judge_calibration_report.py --human-labels datasets/synthetic/human-labels.jsonl --judge-output <judge-output.jsonl>` to compute agreement, Cohen's kappa, confusion matrices, disagreements, and repeated-run variance.
6. Generate Bedrock custom metric definitions from the rubric library with `scripts/build_bedrock_custom_metrics.py --output-dir build/bedrock-custom-metrics`; the generated JSON stays under ignored `build/` unless a scrubbed template needs to be promoted. The committed Week 5 job template is `infra/templates/bedrock-custom-metric-eval-job.json`, with Nova Pro configured as the currently runnable custom-metric evaluator and BYOI placeholders for the model response dataset.
7. Export retrieved/public-source snippets into RAG BYOI rows only when doing grounded-answer compatibility work.

## Current synthetic datasets

- `datasets/synthetic/recruiter-evidence-qa.jsonl` — legacy/native deterministic rows for supported recruiter questions, unsupported overclaims, private-source refusals, inert prompt-injection canaries, and rate-limit/off-topic boundaries.
- `datasets/synthetic/candidate-chat-turns.jsonl` — richer source-of-truth chat-turn rows for the same lanes, including a multi-turn repeated-question case for future live replay.
- `datasets/synthetic/human-labels.jsonl` — Week 5 human-curated calibration labels, one row per recruiter-evidence example and rubric, used as the join target for judge-vs-human agreement.
- Week 5 judge outputs should validate against `schemas/judge-output.schema.json`; keep generated judge outputs separate from human-label fixtures so calibration can compare judge-vs-human instead of smuggling labels into the judge record.
- Week 5 judge model selection lives in `docs/week-05-judge-model-plan.md`: Claude Sonnet primary, Nova Pro comparison, Nova 2 Lite baseline/control.

Week 2 closeout: the expanded synthetic dataset validates locally, the live chatbot capture returns valid responses for all rows, deterministic live scoring passes for all rows, and the captured answers export into valid Bedrock model-eval BYOI JSONL. Bedrock Evaluation jobs are a later execution step; this week validated the input lane and hard gates.

The schema validator is the bouncer. The deterministic scorer is the referee. Bedrock judges come later, once the club is not full of raccoons with fake IDs.
