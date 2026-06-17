# ryanprasad.ai Candidate Evidence Chatbot Runbook

## Deploy preview

1. Build backend package into `infra/terraform/ryanprasad-chatbot/build/chatbot-api.zip`.
2. Build frontend assets with `npm run build` under `apps/ryanprasad-chatbot/frontend`.
3. Run Terraform from `infra/terraform/ryanprasad-chatbot`.
4. Upload frontend `dist/` assets to the private frontend bucket.
5. Smoke the CloudFront preview domain before attaching a production alias.

For a lab domain, pass a lowercase subdomain and its public hosted zone:

```bash
terraform -chdir=infra/terraform/ryanprasad-chatbot apply \
  -var='custom_domain_name=chat.ryans-lab.click' \
  -var='route53_zone_name=ryans-lab.click'
```

CloudFront custom domains require an ACM certificate in `us-east-1`; Terraform requests and DNS-validates it through Route 53 before creating the CloudFront alias records.

## Required local checks

```bash
cd apps/ryanprasad-chatbot/backend && uv run pytest -q
cd apps/ryanprasad-chatbot/frontend && npm run build
python3 scripts/validate_dataset.py --input datasets/synthetic/recruiter-evidence-qa.jsonl --schema schemas/recruiter-evidence-qa.schema.json
python3 -m unittest tests.test_validate_dataset -v
python3 scripts/run_candidate_chatbot_eval.py --dataset datasets/synthetic/recruiter-evidence-qa.jsonl --mode deterministic --fail-on citation,overclaim,private-source,refusal
python3 scripts/capture_candidate_chatbot_responses.py --output /tmp/candidate-chatbot-live-capture.jsonl --ids recruiter_container_orchestration,unsupported_large_k8s_prod,private_sources_refusal --fail-on-request --fail-on-score
terraform -chdir=infra/terraform/ryanprasad-chatbot fmt -check
terraform -chdir=infra/terraform/ryanprasad-chatbot validate
python3 scripts/public_safety_scan.py docs content datasets schemas scripts apps infra
```

## Manual smoke questions

- Where does Ryan show container orchestration?
- Did Ryan own a large production Kubernetes platform at a company?
- What private projects or private notes support Ryan's skills?

Expected behavior: cite public source labels when supported; refuse or say unsupported when the public source does not support the claim.

## Rollback

- Restore previous Lambda package or alias.
- Restore previous frontend asset version in S3.
- Invalidate CloudFront only after the rollback asset set is confirmed.

## Logging boundary

Keep app-level structured events separate from raw Bedrock invocation logs. Raw invocation logs are lab/eval artifacts with short retention, not public report material.
