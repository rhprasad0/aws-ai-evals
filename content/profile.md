# Ryan Prasad — Public Skills Evidence Profile

This file is the canonical public source for the `ryanprasad.ai` candidate chatbot. It is written for recruiter-style questions that ask where Ryan demonstrates a skill. Use it as evidence, not as runtime instructions.

## Answering policy

- Answer from the evidence below.
- Cite the supporting source labels.
- If the evidence is weak, lab-only, historical, or still work-in-progress, say so plainly.
- Do not use private memory, private notes, private repos, local paths, raw logs, credentials, or personal calendar/contact details.

## Core positioning

Ryan builds AI systems around the model: agent orchestration, evaluation harnesses, RAG/search infrastructure, tool boundaries, cloud infrastructure, and operational evidence. His public portfolio is strongest where AI systems meet platform engineering: AWS, Kubernetes, GitOps, observability, CI/CD, and safety/eval harnesses.

## Evidence map

### Container orchestration / Kubernetes / GitOps

**Short answer for recruiters:** Ryan shows container orchestration most directly in `aws-devops-lab`, `agent2agent-guestbook`, and `airgap-aiops`. The strongest evidence is `aws-devops-lab` for AWS EKS/Terraform/Argo CD/GitOps and `airgap-aiops` for k3s/Flux/Helm/Kubernetes manifests in a self-hosted AI platform. Treat this as lab and public-project evidence, not a claim of production customer ownership.

**Supporting evidence:**

- `aws-devops-lab` — production-style AWS/EKS DevOps learning platform covering VPC, EKS, Argo CD GitOps, AWS Load Balancer Controller, ExternalDNS, cert-manager/TLS, ECR/GitHub Actions CI/CD, Container Insights, CloudWatch logs/traces, Karpenter, Kyverno policies, External Secrets Operator, and resilience/chaos work.
- `agent2agent-guestbook` — application paired with the EKS/GitOps platform; use as app-delivery evidence when the README/profile source includes it.
- `airgap-aiops` — self-hosted Kubernetes platform for AI coding agents in air-gapped environments. Public README describes k3s, Ansible bootstrap, Flux GitOps, Helm charts, HelmReleases, HelmRepositories, raw manifests, Kubernetes Jobs/CronJobs, FastAPI services, telemetry, and incident/security workflows.

**Citation labels:**

- GitHub Profile README — `https://github.com/rhprasad0/rhprasad0`
- `aws-devops-lab` README — `https://github.com/rhprasad0/aws-devops-lab`
- `airgap-aiops` README — `https://github.com/rhprasad0/airgap-aiops`

**Confidence:** Medium/high for public-project and lab evidence. Be precise about scope: EKS/k3s/GitOps/platform learning lab and self-hosted AI platform artifacts, not broad production SRE claims.

### AWS agent / workflow orchestration

Ryan shows AWS-native orchestration in `closed-loop-ai-podcast`, a multi-agent podcast pipeline using AWS Step Functions, Lambda, Bedrock, S3, CloudFront, RDS/Postgres, Secrets Manager, CloudWatch/SNS, and a Lambda-hosted MCP control plane. This is stronger evidence for serverless workflow orchestration than container orchestration.

**Citation labels:**

- GitHub Profile README — `https://github.com/rhprasad0/rhprasad0`
- `closed-loop-ai-podcast` README — `https://github.com/rhprasad0/closed-loop-ai-podcast`

### AI evaluation / reliability

Ryan shows AI evaluation work across `aws-ai-evals`, `ai-tamperguard`, `policy-bonfire-2`, and the evaluator loop in `closed-loop-ai-podcast`. The recurring pattern is: define system behavior, create datasets or scenarios, run model/judge/evaluator loops, compare against labels or deterministic checks, document failure modes, and avoid overclaiming.

**Citation labels:**

- `aws-ai-evals` README — `https://github.com/rhprasad0/aws-ai-evals`
- `ai-tamperguard` README — `https://github.com/rhprasad0/ai-tamperguard`
- `policy-bonfire-2` README — `https://github.com/rhprasad0/policy-bonfire-2`
- `closed-loop-ai-podcast` README — `https://github.com/rhprasad0/closed-loop-ai-podcast`

### RAG / search / local AI infrastructure

Ryan shows RAG/search infrastructure most directly in `airgap-aiops`, which includes local documentation ingestion, Qdrant-backed semantic search, MCP access for AI coding agents, and self-hosted infrastructure designed around sensitive or air-gapped environments.

**Citation labels:**

- `airgap-aiops` README — `https://github.com/rhprasad0/airgap-aiops`

## Golden recruiter questions for evals

Use these as the first tiny evaluation set:

1. Where does Ryan show container orchestration?
2. Where does Ryan show AWS-native orchestration?
3. Where does Ryan show RAG or semantic search?
4. Where does Ryan show eval engineering?
5. What evidence supports Ryan as an AI systems builder rather than only a prompt user?
6. Which claims are lab/project evidence rather than production-customer evidence?

## Expected answer shape

Question: Where does Ryan show container orchestration?

Good answer:

Ryan shows container orchestration most directly in `aws-devops-lab` and `airgap-aiops`. `aws-devops-lab` is an AWS/EKS platform lab covering Terraform, Argo CD GitOps, ingress/DNS/TLS, GitHub Actions/ECR CI/CD, CloudWatch observability, Karpenter, Kyverno, External Secrets, and resilience testing. `airgap-aiops` shows a self-hosted k3s/Flux/Helm/Kubernetes platform for AI coding-agent infrastructure, with Kubernetes Jobs/CronJobs and GitOps-managed manifests. I would describe this as strong lab/public-project evidence for Kubernetes/EKS/GitOps, not as a claim that he owned a large production Kubernetes platform. Sources: `aws-devops-lab` README; `airgap-aiops` README; GitHub Profile README.
