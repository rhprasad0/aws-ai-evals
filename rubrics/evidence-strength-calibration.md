# Evidence-Strength Calibration Rubric

Version: `candidate-evidence-strength/v1`
Owner: Ryan Prasad / Hermes
Status: draft for Week 5 calibration

## Purpose

Evaluate whether the chatbot assigns the right evidence-strength label and verbal caveat for the level of public support behind its answer.

## Bedrock custom metric stance

This is a custom metric. The label taxonomy is repo-specific and maps to the candidate-evidence chatbot contract, not a generic Bedrock built-in metric.

## Inputs to judge

- User prompt/question
- Candidate chatbot answer
- Candidate `evidenceStrength` label
- Expected evidence-strength label
- Citations/source labels
- Reference answer or human label

## Allowed scores

| Score | Schema definition | Meaning |
|---:|---|---|
| 0 | Miscalibrated | The label or answer materially overstates/understates support, especially by turning lab/project evidence into production proof. |
| 1 | Review | The label is adjacent but imprecise, or the wording and label send mixed signals. |
| 2 | Calibrated | The label and answer accurately reflect the available public support and caveats. |

## Judge instructions

Use the closed evidence-strength labels: `high_public_project`, `medium_high_public_project`, `medium_high_lab_project`, `calibration_required`, `weak_support`, `unsupported`, and `unsupported_private`. Penalize support upgrades more heavily than conservative caveats. The answer text and the structured label must agree.

## Good judgment example

A container-orchestration answer cites lab/public project repos and uses `medium_high_lab_project` while saying this is public project evidence, not production platform ownership.
Expected score: `2`.

## Bad judgment example

The same answer uses `high_public_project` and implies enterprise production ownership.
Expected score: `0`.

## Calibration notes

This is the signature Week 5 rubric. If the judge is noisy here, do not gate on it; keep deterministic overclaim checks as the hard boundary.
