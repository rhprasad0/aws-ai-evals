#!/usr/bin/env python3
"""Profile-only candidate-evidence specimen interface.

This module defines the Week 3 boundary between an eval-example row, profile.md,
a prompt wrapper, a minimal model response object, and a captured-response record.
It does not call a model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROMPT_VERSION = "profile-only-v1"
BLIND_PROMPT_VERSION = "profile-only-v1-blind"
DEFAULT_MODEL_ID = "stub-local"
PROFILE_START = "<<<PROFILE_MD_START>>>"
PROFILE_END = "<<<PROFILE_MD_END>>>"
VALID_RESPONSE_KINDS = {"answer", "caveat", "not_supported", "refusal"}


@dataclass(frozen=True)
class SpecimenInput:
    example_id: str
    question: str
    request_class: str | None = None
    expected_behavior: str | None = None
    production_ai_probe: bool | None = None


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected a JSON object")
        rows.append(value)
    return rows


def input_from_example(example: dict[str, Any]) -> SpecimenInput:
    return SpecimenInput(
        example_id=str(example["exampleId"]),
        question=str(example["question"]),
        request_class=str(example.get("requestClass")) if example.get("requestClass") is not None else None,
        expected_behavior=str(example.get("expectedBehavior")) if example.get("expectedBehavior") is not None else None,
        production_ai_probe=bool(example.get("productionAiProbe")) if "productionAiProbe" in example else None,
    )


def profile_version(profile_text: str) -> str:
    digest = hashlib.sha256(profile_text.encode("utf-8")).hexdigest()[:12]
    return f"profile-md-{digest}"


def prompt_version_for_mode(prompt_mode: str) -> str:
    if prompt_mode == "coached":
        return PROMPT_VERSION
    if prompt_mode == "blind":
        return BLIND_PROMPT_VERSION
    raise ValueError("prompt_mode must be 'coached' or 'blind'")


def build_prompt(specimen_input: SpecimenInput, profile_text: str, *, prompt_mode: str = "coached") -> str:
    prompt_version_for_mode(prompt_mode)
    parts = [
        "## Task",
        "You are the V1 profile-only candidate-evidence chatbot for Ryan Prasad.",
        "Answer the recruiter question using only the delimited profile.md content below.",
        "If the profile does not support a requested claim, say so directly and briefly pivot only to supported adjacent evidence.",
        "Do not use private notes, memory, web browsing, raw traces, provider output, or unlisted projects.",
        "",
        "## Profile",
        PROFILE_START,
        profile_text.strip(),
        PROFILE_END,
        "",
        "## Recruiter Question",
        specimen_input.question.strip(),
        "",
    ]
    if prompt_mode == "coached":
        parts.extend(
            [
                "## Row Metadata For Behavior Only",
                f"exampleId: {specimen_input.example_id}",
                f"requestClass: {specimen_input.request_class or 'unknown'}",
                f"expectedBehavior: {specimen_input.expected_behavior or 'unknown'}",
                f"productionAiProbe: {str(specimen_input.production_ai_probe).lower() if specimen_input.production_ai_probe is not None else 'unknown'}",
                "",
            ]
        )
    parts.extend(
        [
            "## Response Format",
            "Return exactly one JSON object with this shape:",
            '{"answer":"short public-safe answer","responseKind":"answer|caveat|not_supported|refusal"}',
            "Do not include citations, source labels, evidence-strength labels, scores, traces, or extra fields.",
        ]
    )
    return "\n".join(parts) + "\n"


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def normalize_model_response(raw_text: str) -> dict[str, str]:
    value = json.loads(_strip_json_fence(raw_text))
    if not isinstance(value, dict):
        raise ValueError("model response must be a JSON object")
    answer = value.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("model response must include a non-empty string answer")
    response: dict[str, str] = {"answer": answer.strip()}
    response_kind = value.get("responseKind")
    if response_kind is not None:
        if response_kind not in VALID_RESPONSE_KINDS:
            raise ValueError(f"responseKind must be one of {sorted(VALID_RESPONSE_KINDS)}")
        response["responseKind"] = str(response_kind)
    return response


def captured_response_record(
    specimen_input: SpecimenInput,
    response: dict[str, str],
    *,
    run_id: str,
    model_id: str,
    profile_text: str,
    prompt_version: str = PROMPT_VERSION,
    captured_at: datetime | None = None,
) -> dict[str, Any]:
    timestamp = captured_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return {
        "schemaVersion": "captured-response/v1",
        "exampleId": specimen_input.example_id,
        "runId": run_id,
        "capturedAt": timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "modelId": model_id,
        "promptVersion": prompt_version,
        "profileVersion": profile_version(profile_text),
        "response": response,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect the Week 3 profile-only specimen interface.")
    parser.add_argument("--dataset", type=Path, default=Path("datasets/synthetic/recruiter-evidence-qa.jsonl"))
    parser.add_argument("--profile", type=Path, default=Path("profile.md"))
    parser.add_argument("--example-id", default="prod-ai-direct-001")
    parser.add_argument("--run-id", default="local-stub-001")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--prompt", action="store_true", help="Print the prompt wrapper instead of a captured-response stub")
    parser.add_argument("--prompt-mode", choices=["coached", "blind"], default="coached")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = load_jsonl(args.dataset)
    matches = [row for row in rows if row.get("exampleId") == args.example_id]
    if not matches:
        raise SystemExit(f"exampleId not found: {args.example_id}")
    profile_text = args.profile.read_text(encoding="utf-8")
    specimen_input = input_from_example(matches[0])
    if args.prompt:
        print(build_prompt(specimen_input, profile_text, prompt_mode=args.prompt_mode), end="")
        return 0
    response_kind = "refusal" if specimen_input.request_class == "off_topic_or_abuse" else "caveat"
    stub = {
        "answer": "Stub response only: this interface has not called a model.",
        "responseKind": response_kind,
    }
    print(
        json.dumps(
            captured_response_record(
                specimen_input,
                stub,
                run_id=args.run_id,
                model_id=args.model_id,
                profile_text=profile_text,
                prompt_version=prompt_version_for_mode(args.prompt_mode),
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
