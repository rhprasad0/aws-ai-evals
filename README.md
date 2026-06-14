# AWS AI Evals

Hands-on learning plan for building AWS-native and hybrid AI evaluation harnesses.

This repo is a public-safe working artifact for learning by doing: datasets, trace
contracts, Bedrock model/RAG evals, AgentCore evals, Inspect AI, custom scorers,
orchestration, CI gates, observability, and cost/security controls.

Start here:

- [`docs/aws-ai-evals-learning-plan.md`](docs/aws-ai-evals-learning-plan.md) — 12-week hands-on roadmap

## What this is

A public-safe AI Engineering artifact for learning AWS eval harnesses by building one:

- Bedrock model evaluations and custom metrics
- Bedrock RAG retrieval/retrieve-and-generate evaluations
- Bedrock AgentCore agent/tool evaluations
- Inspect AI custom evals on AWS
- dataset adapters, validators, deterministic scorers, run manifests, reports, and CI gates

## Scope, honestly

This is a learning artifact, not a production eval service. Managed Bedrock evaluations are
one *component* — the dataset contracts, validators, fan-out, judges, scorers, orchestration,
and receipts around them are the actual harness. BYOI means you supply pre-generated inference
responses in AWS's expected shape, not that AWS runs your live app. LLM-as-judge scores are
measurements with error bars, not ground truth. Everything here runs on synthetic data and
placeholder identifiers.

## Status

WIP learning plan. No credentials, live AWS account details, private traces, real
customer/user data, or working attack payloads (jailbreaks, exploit code) belong in this
repository — the safety and prompt-injection lanes use inert canaries, not copy-pasteable
exploits.
