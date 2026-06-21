# Completeness Rubric

Version: `candidate-completeness/v1`
Owner: Ryan Prasad / Hermes
Status: draft for Week 5 calibration

## Purpose

Evaluate whether the answer covers the required parts of the recruiter question without padding with unsupported claims. Completeness is bounded coverage, not maximal verbosity.

## Bedrock custom metric stance

Bedrock has a built-in completeness metric, but this custom rubric narrows completeness to the candidate-evidence chatbot: answer the user's evidence question, include relevant public support, mention limitations when support is weaker than the question implies, and avoid résumé fan fiction.

## Inputs to judge

- User prompt/question
- Candidate chatbot answer
- Reference answer or must-include labels
- Expected evidence strength
- Expected citations/source labels

## Allowed scores

| Score | Schema definition | Meaning |
|---:|---|---|
| 0 | Incomplete | The answer misses the main requested evidence, omits necessary caveats, or refuses when public evidence supports an answer. |
| 1 | Partially complete | The answer addresses the question but misses an important source, caveat, or required distinction. |
| 2 | Complete | The answer covers the requested evidence, cites the relevant public sources, and includes the right limitation/caveat when needed. |

## Judge instructions

Score against the user question, not against an imaginary exhaustive biography. Prefer concise answers that cover the requested evidence over bloated answers. Penalize missing required source labels, missing evidence-strength caveats, and answers that dodge supported recruiter questions.

## Good judgment example

Question: "Where does Ryan show AWS infrastructure?"
Answer: names the relevant public project source and explains what it demonstrates, while keeping the claim scoped.
Expected score: `2`.

## Bad judgment example

Question: "Where does Ryan show container orchestration?"
Answer: mentions only one weakly related project and omits the stronger expected public sources.
Expected score: `1` or `0`, depending on whether the remaining answer still addresses the core question.

## Calibration notes

Track false incompleteness penalties: a short but properly bounded answer can be complete. Verbosity should not buy points by itself.
