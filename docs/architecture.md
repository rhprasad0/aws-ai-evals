# Architecture

## V1 Shape

The V1 candidate-evidence chatbot is a small local lab specimen, not a production architecture. Its job is to prove that a profile-only source and coarse pass/fail labels are enough to evaluate recruiter-facing answers before adding retrieval, judges, Bedrock jobs, UI polish, or deployment.

```text
profile.md
  -> prompt wrapper
  -> model
  -> minimal JSON response
  -> captured response record
  -> human pass/fail label
```

## Components

### `profile.md`

`profile.md` is the only chatbot source. It summarizes GitHub-backed public evidence, claim limits, and the correct production-AI caveat. GitHub is upstream evidence, but the chatbot does not browse or retrieve GitHub at answer time.

If a fact is not in `profile.md`, the chatbot should treat it as unsupported.

### Prompt wrapper

The prompt wrapper:

- tells the model this is recruiter-facing candidate evidence Q&A;
- inserts `profile.md` as evidence, not instructions;
- separates instructions, profile evidence, and the user question;
- asks for minimal JSON with `answer` and optional `responseKind`.

It does not include tools, memory, retrieval, citations, source labels, hidden scoring rubrics, or résumé-expansion logic.

### Model response

The model returns minimal JSON:

```json
{
  "answer": "string",
  "responseKind": "answer | caveat | not_supported | refusal"
}
```

`responseKind` is optional debugging metadata. The human label is still based on the answer and the dataset row, not the model's self-classification.

### Captured response record

A capture wrapper stores enough metadata to connect the model output to the dataset row and run:

- `exampleId`
- `runId`
- `capturedAt`
- `modelId`
- `promptVersion`
- `profileVersion`
- `response`

There is no full manifest system in V1.

### Human label

Human review produces a binary label:

- `pass`
- `fail`

Optional failure tags explain why a row failed. Production AI overclaiming is the central failure mode to stress in early examples.

## Explicit Non-Components

V1 does not include:

- source ledger;
- citation policy;
- evidence-strength taxonomy;
- RAG or live GitHub retrieval;
- Honcho, Graphiti, Hermes memory, or local notes;
- Bedrock managed evaluation jobs;
- judge rubrics or model-as-judge calibration;
- Step Functions or orchestration;
- AWS IAM/KMS/S3 infrastructure;
- public deployment or UI polish.

Add these only after the profile/dataset/schema/label workflow is easy to validate and label.

## Data Flow

1. A dataset row provides a recruiter-style `question` plus expected coarse behavior.
2. The local runner loads `profile.md` and builds the prompt.
3. The model returns minimal JSON.
4. The runner stores a captured response record with lightweight run metadata.
5. A human labels the response `pass` or `fail` against `profile.md` and the dataset row.
6. Validators check JSON shape, required fields, enum values, and stable IDs.

## Production AI Boundary

Most recruiter prompts will try to answer one question: does Ryan have production AI experience?

Current V1 answer: the public profile should not support a production-AI experience claim. The chatbot should say that candidly and then pivot to GitHub-backed adjacent evidence: AI evaluation work, AWS implementation, agent/tooling experiments, and operational discipline.

A response fails if it implies Ryan has shipped, owned, operated, monitored, or supported production AI systems when `profile.md` does not support that claim.
