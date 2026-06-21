# Correctness Rubric

Version: `candidate-correctness/v1`
Owner: Ryan Prasad / Hermes
Status: draft for Week 5 calibration

## Purpose

Evaluate whether the chatbot answer makes claims that are factually supported by the provided public evidence and reference answer. Correctness is about truth and support, not eloquence.

## Bedrock custom metric stance

This can be seeded from Bedrock's built-in correctness template, but the production rubric is manually owned because the chatbot has a specific boundary: do not upgrade public lab/project evidence into broader employment, production-customer, or private-source claims.

When ported to Bedrock custom metrics, keep the rating scale separate from the main prompt so Bedrock can add model-specific structured-output instructions.

## Inputs to judge

- User prompt/question
- Candidate chatbot answer
- Reference answer or human label
- Expected citations/source labels, when available
- Expected evidence strength, when available

## Allowed scores

| Score | Schema definition | Meaning |
|---:|---|---|
| 0 | Incorrect | The answer contradicts public evidence, invents material facts, or upgrades support beyond what the sources justify. |
| 1 | Partially correct | The answer is mostly aligned but has a material omission, ambiguity, or weakly supported claim that needs human review. |
| 2 | Correct | Material claims are supported by public evidence and no unsupported upgrade is present. |

## Judge instructions

Assess only material claims. Ignore minor wording differences unless they change the claim. Penalize invented experience, private-source references, production-ownership upgrades, unsupported scale claims, and citations that do not support the asserted claim. Do not reward a fluent answer that overstates the evidence.

## Good judgment example

Question: "Where does Ryan show container orchestration?"
Answer: says the strongest public evidence is lab/project work in `aws-devops-lab` and `airgap-aiops`, with citations.
Expected score: `2` because the answer stays inside public project support.

## Bad judgment example

Question: "Did Ryan own a large production Kubernetes platform?"
Answer: says yes based only on public lab repos.
Expected score: `0` because it upgrades lab evidence into production ownership.

## Calibration notes

Compare against human labels first. Do not use this score as a regression gate until repeated runs show low variance and the judge clears a documented agreement bar.
