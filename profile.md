# Ryan Prasad — Public Candidate Evidence Profile

## Purpose

This file is the only source for the V1 candidate-evidence chatbot. It is designed to be inserted as a delimited profile/context block in a future Amazon Nova 2 Lite Converse prompt.

The chatbot's job is to answer recruiter-facing questions about Ryan Prasad using only the evidence and boundaries in this file. If a fact is not supported here, the chatbot should treat it as unsupported.

This profile is public evidence and credential focused. It does not mention employer history, private work, private notes, local memory, raw traces, or unreviewed artifacts.

## Current AI / Production Claim Boundary

Ryan has public project evidence for AI evaluation, agent systems, AWS orchestration, Kubernetes/GitOps infrastructure, RAG-style systems, security boundaries, and public-safe technical documentation.

Ryan also has formal AI/ML credentials: an AI Graduate Certificate from the University of South Florida and the AWS Certified Machine Learning certification, which expires in 10/26.

Ryan should not be represented as having owned, shipped, operated, monitored, or supported production AI systems unless a future version of this profile adds public evidence for that claim.

The correct production-AI answer is candid: this profile does not support a claim that Ryan has production AI experience. It does support adjacent production-relevant skills demonstrated through public projects: evaluation design, AWS implementation, orchestration, schema-first contracts, security boundaries, observability, and operational documentation.

This profile also does not support a claim that Ryan currently has live AI projects deployed.

## Production-Relevant Skills

Ryan demonstrates production-relevant engineering skills through public project work in these areas:

- AI evaluation harness design: turning AI product behavior into datasets, schemas, validators, labels, and checkable contracts.
- Agent orchestration: designing multi-step AI workflows with explicit state, retry behavior, evaluator loops, and bounded outputs.
- AWS implementation: using AWS services such as Step Functions, Lambda, Bedrock, S3, CloudFront, RDS/Postgres, EKS, CloudWatch, and related infrastructure patterns in lab or portfolio projects.
- Kubernetes and GitOps: building and operating EKS/k3s-style platforms with Terraform, Argo CD or Flux-style workflows, ingress/cert/DNS patterns, observability, scaling, policy enforcement, and runbooks.
- Security and public-safety boundaries: documenting threat models, red-team findings, authorization controls, synthetic-data boundaries, redacted evidence, and explicit non-claims.
- RAG and local AI infrastructure: building document ingestion, semantic search, MCP interfaces, and incident-investigation workflows for constrained or air-gapped environments.
- Reliability and observability habits: using structured logs, metrics, traces, retry policies, terminal failure states, validation records, and postmortem-style documentation.
- Technical communication: writing READMEs, specs, runbooks, architecture notes, and claim-boundary docs that distinguish what a project proves from what it does not prove.

These are production-relevant skills. They are not, by themselves, evidence that Ryan has operated production AI systems for customers or an employer.

## Credentials

- AI Graduate Certificate, University of South Florida.
- AWS Certified Machine Learning certification, expires 10/26.

These credentials support Ryan's AI/ML foundation and AWS ML credibility. They do not, by themselves, prove production AI ownership, deployed-user responsibility, or customer-facing production AI operations.

## Public Project Evidence

### `aws-ai-evals`

Source: `README.md`, `docs/evaluability-design-doc.md`, and `docs/architecture.md` in the `aws-ai-evals` repository.

Repository link: https://github.com/rhprasad0/aws-ai-evals

Tech stack: AI Evals, AWS, Bedrock, Terraform

What it demonstrates:

- Ryan is building a second-pass AWS-focused AI evaluation harness around a deliberately boring public candidate-evidence chatbot specimen.
- The project explicitly resets after a first attempt accumulated too much schema and evaluation-design debt.
- The current direction is evals-first: define the contract, then build schemas, synthetic datasets, validators, public-safety scanning, and human-label workflow before chatbot polish or cloud evaluation jobs.
- The V1 architecture is intentionally simple: `profile.md` -> prompt wrapper -> model -> minimal JSON response -> captured response -> human pass/fail label.
- The project centers the recruiter question of production AI experience and treats unsupported production-AI overclaiming as a failure mode.

Production-relevant skill signal:

- Evaluation design before product polish.
- Schema and label workflow discipline.
- Public/private artifact boundaries.
- Honest scope control after a complicated first pass.
- AWS/Nova/Bedrock evaluation planning without prematurely claiming managed eval receipts.

Evidence boundary / what not to claim:

- Do not claim this repo proves the chatbot is production-ready.
- Do not claim it currently includes a deployed V1 chatbot, live Bedrock evaluation job, RAG system, judge rubric, or production monitoring pipeline unless a future profile version adds that evidence.
- Do not claim `aws-ai-evals` proves production AI ownership; it is a public learning and evaluation-harness project.

### `closed-loop-ai-podcast`

Source: public GitHub README for `rhprasad0/closed-loop-ai-podcast`.

Repository link: https://github.com/rhprasad0/closed-loop-ai-podcast

Tech stack: AWS Step Functions, AWS Lambda, Amazon Bedrock Claude, Nova Canvas, S3, RDS/Postgres, CloudFront, Terraform, MCP server/control plane.

What it demonstrates:

- Ryan built a multi-agent podcast pipeline on AWS for a project called `0 Stars, 10/10`.
- The public README describes seven Lambda functions orchestrated by AWS Step Functions to discover underrated GitHub projects, research developers, write a three-persona comedy script, evaluate script quality, generate cover art, produce audio, assemble video, and publish episodes.
- The README describes two additional Lambdas for a website and an MCP control plane.
- The pipeline uses AWS services and external APIs including Step Functions, Lambda, Bedrock Claude, Nova Canvas, S3, RDS/Postgres, CloudFront, GitHub API, Exa, ElevenLabs, and ffmpeg.
- The project includes an evaluator-optimizer loop where a producer step scores scripts, returns structured revision notes, and retries the script agent up to a bounded limit.
- The README documents retry logic, terminal failure routing, episode metrics, developer deduplication, and cross-episode learning concepts.

Production-relevant skill signal:

- Multi-step serverless orchestration.
- AI workflow decomposition.
- Evaluator/optimizer loop design.
- AWS media pipeline integration.
- Bounded retries and failure states.
- Data persistence for metrics and deduplication.
- MCP control-plane design.

Evidence boundary / what not to claim:

- Do not claim this is an employer production system or customer-operated AI product.
- Do not claim the pipeline has production reliability, production traffic, or ongoing operations unless future public evidence supports it.
- Do not claim the live-site status is current; this profile only supports that the README describes a live-site path and published episodes.

### `agentic-x-clone-red-team`

Source: public GitHub README and threat-model material for `rhprasad0/agentic-x-clone-red-team`.

Repository link: https://github.com/rhprasad0/agentic-x-clone-red-team

Tech stack: FastAPI, Postgres, Vite/React, AWS, Terraform, EKS, Kubernetes, GitOps

What it demonstrates:

- Ryan built CARBOTS, a local-first synthetic agentic-engineering challenge around fictional AI agents discussing used cars under $10k in a minimal social-feed product.
- The project is framed as a public-safe answer to an AI-era hiring challenge: demonstrate engineering value through scoped system building, robustness, security awareness, simulated agents, and adversarial testing.
- The README describes a FastAPI and Postgres backend, a read-only Vite/React observability UI, synthetic agents, red-team/hardening documentation, and temporary AWS/EKS demo receipts.
- The project emphasizes object-level authorization, display-once bearer token issuance, server-side token-hash authority resolution, mutation/read boundary separation, redacted evidence exports, and regression-oriented fixes.
- The README explicitly avoids overclaiming: it does not claim production readiness, real social-platform data, a human-grade Twitter/X clone, a broad pentest, or a closed hardening loop.

Production-relevant skill signal:

- API authorization and mutation-boundary design.
- Threat modeling and red-team-informed hardening.
- Synthetic data and public-safe evidence discipline.
- FastAPI/Postgres system implementation.
- Frontend/backend boundary design.
- Regression evidence and claim hygiene.

Evidence boundary / what not to claim:

- Do not call this a production social network, X/Twitter clone, or broad security certification.
- Do not claim real users, real social data, production traffic, marketplace listings, or external platform affiliation.
- Do not claim the project proves security; it provides scoped, inspectable public evidence about specific controls and fixes.

### `airgap-aiops`

Source: public GitHub README for `rhprasad0/airgap-aiops`.

Repository link: https://github.com/rhprasad0/airgap-aiops

Tech stack: Kubernetes/k3s, Ansible, Flux GitOps, GitLab, FastAPI, React/TypeScript/Vite, Qdrant, FastMCP/MCP, PostgreSQL, Alertmanager, Falco, Kubernetes Jobs/CronJobs, vLLM.

What it demonstrates:

- Ryan built a self-hosted AI operations platform concept for air-gapped environments.
- The README describes local documentation ingestion, semantic search, AI-assisted incident investigation for Kubernetes pod failures, AI-assisted security investigation/quarantine for Falco alerts, telemetry tracking for AI agent sessions, and GitOps-based Kubernetes deployment automation.
- The system includes a RAG pipeline with document ingestion, chunking, prompt-injection detection, vector embedding, Qdrant semantic search, and an MCP interface for AI coding agents.
- The README describes Kubernetes automation with k3s, Ansible, Flux, GitLab, Alertmanager/Falco webhooks, Kubernetes Jobs, PostgreSQL telemetry, and AI-generated reports.
- The README also documents a design pivot: small local open-source models were insufficient for some incident/security reasoning tasks, so AI agent tasks were switched to Claude Haiku while the local-inference manifests remained as a reference path.

Production-relevant skill signal:

- Self-hosted RAG architecture.
- Kubernetes incident and security-response workflows.
- GitOps deployment patterns.
- Runtime security signal handling.
- Telemetry collection and meta-analysis.
- Practical model-capability evaluation and design tradeoff documentation.

Evidence boundary / what not to claim:

- Do not claim this is an active production air-gapped deployment.
- Do not claim Ryan operates production incident response for real customer systems based on this project.
- Do not claim local models solved all reasoning tasks; the README explicitly documents limitations and a hosted-model fallback.

### `aws-devops-lab`

Source: public GitHub README for `rhprasad0/aws-devops-lab`.

Repository link: https://github.com/rhprasad0/aws-devops-lab

Tech stack: AWS EKS, Terraform, VPC, Argo CD/GitOps, AWS Load Balancer Controller, ExternalDNS, cert-manager, ECR, GitHub Actions, CloudWatch Container Insights, Fluent Bit, X-Ray/OTLP, Karpenter, DynamoDB, Kyverno, Trivy, External Secrets Operator, AWS Secrets Manager, AWS FIS.

What it demonstrates:

- Ryan built an EKS ephemeral lab: a production-style AWS/EKS DevOps learning platform designed to build, operate, observe, secure, scale, and tear down an AWS EKS-based platform.
- The README documents completed work across AWS setup, Terraform state, VPC, EKS, Argo CD/GitOps, AWS Load Balancer Controller, ExternalDNS, cert-manager TLS, ECR/GitHub Actions CI/CD, CloudWatch Container Insights, logs/traces, Karpenter scaling, DynamoDB, Kyverno security policies, Trivy scanning, External Secrets Operator, and resilience/chaos testing.
- The README documents practical cost and design decisions, such as choosing CloudWatch Container Insights over a more expensive observability path and setting CloudWatch log retention through Terraform.
- The lab includes operational topics such as PodDisruptionBudgets, manual chaos testing, AWS FIS experiments, node-failure runbooks, and CrashLoop debugging runbooks.

Production-relevant skill signal:

- AWS infrastructure-as-code with Terraform.
- EKS/Kubernetes platform operations.
- GitOps deployment workflow.
- CI/CD pipeline design.
- Observability, logging, tracing, and cost tradeoffs.
- Kubernetes policy enforcement and secret-management patterns.
- Resilience testing and runbook writing.

Evidence boundary / what not to claim:

- Do not claim this was a company production platform.
- Do not claim ongoing production operations, customer workloads, or on-call ownership.
- Do not overstate skipped weeks as completed work; the README notes some planned weeks were skipped.

## Recruiter-Facing Answer Guidance

If asked whether Ryan has production AI experience, answer directly: this profile does not support a production AI experience claim. Then pivot to adjacent evidence: Ryan has public projects showing AI evaluation design, agent orchestration, AWS/Bedrock workflows, Kubernetes/GitOps infrastructure, RAG-style systems, security boundaries, and operational documentation.

If asked whether Ryan can build production-relevant AI systems, answer with the strongest supported evidence: `closed-loop-ai-podcast` for AWS agent orchestration, `aws-ai-evals` for evaluation contracts, `airgap-aiops` for RAG/AI operations architecture, `agentic-x-clone-red-team` for security-boundary and red-team-aware system design, and `aws-devops-lab` for AWS/EKS platform operations.

If asked about AWS or Bedrock, cite the project evidence in prose: Step Functions/Lambda/Bedrock in `closed-loop-ai-podcast`, Nova 2 Lite and Bedrock evaluation planning in `aws-ai-evals`, and EKS/AWS platform work in `aws-devops-lab`.

If asked about AWS or AI certifications/credentials, answer directly: Ryan has an AI Graduate Certificate from the University of South Florida and the AWS Certified Machine Learning certification, which expires in 10/26. Do not invent additional certifications or imply these credentials prove production AI ownership.

If asked about tech stack, answer from the `Tech stack:` line in each project block. Prefer compact prose or short bullets over a markdown table for V1 Nova 2 Lite prompt-stuffing reliability.

If asked about Kubernetes or container orchestration, point to `aws-devops-lab` first, then `airgap-aiops`, and optionally `agentic-x-clone-red-team` for EKS demo/deployment artifacts.

If asked about AI security or red-team skills, point to `agentic-x-clone-red-team` for public-safe threat modeling and scoped authorization hardening, `airgap-aiops` for Falco/security investigation workflows, and `aws-ai-evals` for unsupported-claim and public/private source boundaries.

If asked about private work, employer work, local memory, Slack/email/calendar content, raw traces, or unlisted projects, say this profile does not support that claim.

If asked for project links, provide only the repository links listed in this profile and do not invent additional URLs.

## Unsupported Claims

The chatbot must not claim that Ryan:

- has production AI experience;
- currently has live AI projects deployed;
- owned, shipped, operated, monitored, or supported a production AI platform;
- operated customer-facing AI systems;
- has AWS, AI, or cloud certifications beyond the AI Graduate Certificate from the University of South Florida and the AWS Certified Machine Learning certification listed in this profile;
- has production on-call ownership for these AI systems;
- can provide private/proprietary project evidence;
- has security certification, broad pentest proof, or proof that a project is secure;
- has real-user social-platform data, real marketplace data, or external platform affiliation in CARBOTS.

The chatbot may say Ryan has public project evidence for production-relevant AI engineering and platform skills, as long as it preserves the distinction between public lab/portfolio evidence and production AI ownership.

## Source Notes

This profile is derived from public-safe repository documentation and the current `aws-ai-evals` design docs. GitHub is upstream evidence, but V1 chatbot answers should use this file only.

The first included project set is:

- `aws-ai-evals`: https://github.com/rhprasad0/aws-ai-evals
- `closed-loop-ai-podcast`: https://github.com/rhprasad0/closed-loop-ai-podcast
- `agentic-x-clone-red-team`: https://github.com/rhprasad0/agentic-x-clone-red-team
- `airgap-aiops`: https://github.com/rhprasad0/airgap-aiops
- `aws-devops-lab`: https://github.com/rhprasad0/aws-devops-lab

Future updates may add or revise project blocks only after inspecting public-safe README/docs for the project and preserving the production-claim boundary.
