# Candidate Evidence Chatbot Eval Gates

The chatbot is the specimen; the eval harness is the learning artifact.

## Deterministic gate

Run schema validation before scoring:

```bash
python3 scripts/validate_dataset.py \
  --schema schemas/recruiter-evidence-qa.schema.json \
  --input datasets/synthetic/recruiter-evidence-qa.jsonl
python3 -m unittest tests.test_validate_dataset -v
```

Then run the deterministic content gate before deploy:

```bash
python3 scripts/run_candidate_chatbot_eval.py \
  --dataset datasets/synthetic/recruiter-evidence-qa.jsonl \
  --mode deterministic \
  --fail-on citation,overclaim,private-source,refusal
```

The deterministic gate checks:

- supported answers include expected public source labels;
- nonexistent citation labels are rejected;
- required evidence phrases appear;
- forbidden production-ownership upgrades are not asserted;
- unsupported/private-source questions refuse or say the public source does not support the claim.

## Live/local response capture

Use the capture gate to replay dataset rows against a live or local `/api/chat` endpoint, validate each response through the backend response contract, and run deterministic scoring on the captured output:

```bash
python3 scripts/capture_candidate_chatbot_responses.py \
  --endpoint https://chat.ryans-lab.click/api/chat \
  --output /tmp/candidate-chatbot-live-capture.jsonl \
  --ids recruiter_container_orchestration,unsupported_large_k8s_prod,private_sources_refusal \
  --fail-on-request \
  --fail-on-score
```

Keep capture outputs in `/tmp`, `results/`, or another ignored lab path unless they have been reviewed and promoted as public-safe receipts.

## BYOI export gate

Once responses are captured, convert them into Bedrock model-eval BYOI JSONL and validate the AWS export lane:

```bash
python3 scripts/bedrock_byoi_adapter.py \
  --dataset datasets/synthetic/recruiter-evidence-qa.jsonl \
  --input /tmp/week2-live-byoi-YYYYMMDDTHHMMSSZ/live-capture.jsonl \
  --output /tmp/week2-live-byoi-YYYYMMDDTHHMMSSZ/bedrock-model-eval-byoi.jsonl \
  --model-identifier ryanprasad-ai-chatbot-v1-live-<git-sha>

python3 scripts/validate_dataset.py \
  --schema schemas/bedrock-model-eval-byoi.schema.json \
  --input /tmp/week2-live-byoi-YYYYMMDDTHHMMSSZ/bedrock-model-eval-byoi.jsonl
```

A BYOI export can be valid even when deterministic scoring found failures. That is useful for judge calibration, but it is not a clean regression pass until the deterministic failures are triaged. The Week 2 closeout rerun produced a clean live deterministic pass before regenerating the BYOI JSONL.

## BYOI regression batch

Use captured chatbot answers to build Bedrock model-as-judge BYOI rows:

```bash
python3 scripts/bedrock_byoi_adapter.py \
  --input /tmp/candidate-chatbot-answers.jsonl \
  --output /tmp/candidate-chatbot-byoi.jsonl \
  --model-identifier ryanprasad-ai-chatbot-v1
```

Each BYOI row uses:

- `prompt`
- `referenceResponse`
- `category`
- `modelResponses[].response`
- `modelResponses[].modelIdentifier`

Use one `modelIdentifier` per Bedrock evaluation job.

## Judge calibration

Run model-as-judge batches three times before trusting movement in judge scores. Compare against human labels and treat high-variance prompts as review items, not automatic deploy blockers.
