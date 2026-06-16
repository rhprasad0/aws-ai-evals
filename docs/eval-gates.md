# Candidate Evidence Chatbot Eval Gates

The chatbot is the specimen; the eval harness is the learning artifact.

## Deterministic gate

Run before deploy:

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
