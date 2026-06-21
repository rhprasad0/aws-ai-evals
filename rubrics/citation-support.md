# Citation Support Rubric

Version: `candidate-citation-support/v1`
Owner: Ryan Prasad / Hermes
Status: draft for Week 5 calibration

## Purpose

Evaluate whether the answer's citations actually support the material claims they are attached to, using only the closed public source-label set.

## Bedrock custom metric stance

This is a custom metric. Bedrock's generic quality metrics do not know the chatbot's allowed citation labels or the rule that unsupported/private answers should generally have no citations.

## Inputs to judge

- User prompt/question
- Candidate chatbot answer
- Candidate citation labels
- Expected citation labels
- Reference answer/source notes

## Allowed scores

| Score | Schema definition | Meaning |
|---:|---|---|
| 0 | Unsupported | Citations are missing for material supported claims, invalid, fabricated, or attached to claims they do not support. |
| 1 | Partially supported | Citations are valid but incomplete, overly broad, or support only part of the answer. |
| 2 | Supported | Material claims have valid public source labels and the cited sources support the claims. |

## Judge instructions

Use the repo's closed citation-label contract as the authority. Valid labels include `content/profile.md`, `GitHub Profile README`, and public project README labels such as `aws-devops-lab README` and `airgap-aiops README`. Penalize unknown labels, private-source references, citations on unsupported refusals when no public support exists, and claims whose citation only loosely gestures at support.

## Good judgment example

Answer says container orchestration is supported by `aws-devops-lab README` and `airgap-aiops README` and keeps the claim to lab/public-project evidence.
Expected score: `2`.

## Bad judgment example

Answer cites `content/profile.md` for a claim that Ryan owned a large production Kubernetes platform.
Expected score: `0` because the citation does not support the upgraded claim.

## Calibration notes

Compare this rubric against deterministic citation gates. The judge should add nuance about whether citations support claims, while deterministic checks remain the hard guard for unknown labels.
