#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - dependency guard for fresh machines
    raise SystemExit("scoring failed: install jsonschema to use scripts/score_app_events.py") from exc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "schemas" / "aws-evals" / "normalized-app-event.schema.json"
UNSUPPORTED_LABELS = {"unsupported", "unsupported_private"}
SUPPORTED_LABELS = {"high_public_project", "medium_high_public_project", "medium_high_lab_project", "weak_support"}
TOKEN_FIELDS = {"input_tokens", "output_tokens", "total_tokens"}


@dataclass(frozen=True)
class AppEventScore:
    row_number: int
    passed: bool
    issues: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministically score normalized candidate-chatbot app-event JSONL.")
    parser.add_argument("--input", required=True, type=Path, help="Normalized app-event JSONL file.")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--max-latency-ms", type=int, default=5000)
    parser.add_argument("--max-total-tokens", type=int, default=4000)
    parser.add_argument("--fail-on-score", action="store_true", help="Exit non-zero if any app-event score fails.")
    return parser.parse_args()


def load_schema(path: Path) -> dict[str, Any]:
    schema = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise ValueError("schema root must be a JSON object")
    Draft202012Validator.check_schema(schema)
    return schema


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_no}: invalid JSON at column {exc.colno}: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"line {line_no}: event must be a JSON object")
        events.append(payload)
    if not events:
        raise ValueError("input contains no app events")
    return events


def schema_issues(events: Iterable[dict[str, Any]], schema: dict[str, Any]) -> dict[int, list[str]]:
    validator = Draft202012Validator(schema)
    by_row: dict[int, list[str]] = {}
    for row_number, event in enumerate(events, 1):
        for exc in sorted(validator.iter_errors(event), key=lambda item: list(item.absolute_path)):
            path = "." + ".".join(str(part) for part in exc.absolute_path) if exc.absolute_path else ""
            by_row.setdefault(row_number, []).append(f"schema{path}: {exc.message}")
    return by_row


def score_event(event: dict[str, Any], *, max_latency_ms: int, max_total_tokens: int) -> list[str]:
    issues: list[str] = []
    citation_labels = event.get("citation_labels", [])
    citation_count = event.get("citation_count")
    evidence_strength = event.get("evidence_strength")
    response_source = event.get("response_source")

    if isinstance(citation_labels, list) and isinstance(citation_count, int) and citation_count != len(citation_labels):
        issues.append(f"citation_count mismatch: expected {len(citation_labels)}, got {citation_count}")

    if evidence_strength in UNSUPPORTED_LABELS:
        if citation_count != 0 or citation_labels:
            issues.append("unsupported event must not carry citations")
        if event.get("unsupported_claim_count", 0) < 1:
            issues.append("unsupported event must record at least one unsupported claim")
    elif evidence_strength in SUPPORTED_LABELS:
        if response_source != "bedrock":
            issues.append("supported evidence labels should come from bedrock responses")
        if citation_count == 0:
            issues.append("supported event must include at least one citation")

    if response_source == "bedrock":
        elapsed_ms = event.get("elapsed_ms")
        if isinstance(elapsed_ms, int) and elapsed_ms > max_latency_ms:
            issues.append(f"latency budget exceeded: {elapsed_ms}ms > {max_latency_ms}ms")
        token_values = {field: event.get(field) for field in TOKEN_FIELDS if field in event}
        if token_values:
            missing = sorted(TOKEN_FIELDS - token_values.keys())
            if missing:
                issues.append(f"partial token usage: missing {missing}")
            input_tokens = event.get("input_tokens")
            output_tokens = event.get("output_tokens")
            total_tokens = event.get("total_tokens")
            if isinstance(input_tokens, int) and isinstance(output_tokens, int) and isinstance(total_tokens, int):
                if total_tokens != input_tokens + output_tokens:
                    issues.append(
                        f"token total mismatch: input_tokens + output_tokens = {input_tokens + output_tokens}, got {total_tokens}"
                    )
                if total_tokens > max_total_tokens:
                    issues.append(f"token budget exceeded: {total_tokens} > {max_total_tokens}")
    elif response_source == "guardrail":
        present_token_fields = sorted(TOKEN_FIELDS & event.keys())
        if present_token_fields:
            issues.append(f"guardrail event must not include token fields: {present_token_fields}")

    return issues


def score_events(
    events: list[dict[str, Any]],
    *,
    schema: dict[str, Any],
    max_latency_ms: int,
    max_total_tokens: int,
) -> list[AppEventScore]:
    schema_by_row = schema_issues(events, schema)
    scores: list[AppEventScore] = []
    for row_number, event in enumerate(events, 1):
        issues = list(schema_by_row.get(row_number, []))
        if not issues:
            issues.extend(score_event(event, max_latency_ms=max_latency_ms, max_total_tokens=max_total_tokens))
        scores.append(AppEventScore(row_number=row_number, passed=not issues, issues=issues))
    return scores


def summarize(events: list[dict[str, Any]], scores: list[AppEventScore]) -> dict[str, Any]:
    failed = [score for score in scores if not score.passed]
    return {
        "events": len(events),
        "passed": len(events) - len(failed),
        "failed": len(failed),
        "response_sources": _counts(event.get("response_source") for event in events),
        "evidence_strengths": _counts(event.get("evidence_strength") for event in events),
        "failures": [{"row": score.row_number, "issues": score.issues} for score in failed],
    }


def _counts(values: Iterable[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def main() -> int:
    args = parse_args()
    try:
        schema = load_schema(args.schema)
        events = load_jsonl(args.input)
        scores = score_events(
            events,
            schema=schema,
            max_latency_ms=args.max_latency_ms,
            max_total_tokens=args.max_total_tokens,
        )
    except Exception as exc:
        print(f"scoring failed: {exc}", file=sys.stderr)
        return 1
    summary = summarize(events, scores)
    summary["input"] = str(args.input)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.fail_on_score and summary["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
