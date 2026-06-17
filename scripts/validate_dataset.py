#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError, ValidationError
except ImportError as exc:  # pragma: no cover - dependency guard for fresh machines
    raise SystemExit("validation failed: install jsonschema to use scripts/validate_dataset.py") from exc

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_SAFETY_PATTERNS: dict[str, re.Pattern[str]] = {
    "private_home_path": re.compile(r"/home/[A-Za-z0-9._-]+"),
    "windows_user_path": re.compile(r"[A-Za-z]:\\\\Users\\\\[A-Za-z0-9._-]+"),
    "slack_channel_id": re.compile(r"\bC0[A-Z0-9]{8,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "secret_token": re.compile(r"\b(?:sk|gh[pousr]|xox[baprs])-[-A-Za-z0-9_]{16,}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    "private_ip": re.compile(r"\b(?:10\.\d{1,3}|172\.(?:1[6-9]|2[0-9]|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b"),
    "email_address": re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.com\b|example\.org\b|example\.net\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "aws_account_id": re.compile(r"\barn:aws:[^\s:]+:[a-z0-9-]*:\d{12}:[^\s]+|\b\d{12}\b"),
    "private_hostname": re.compile(r"\b[A-Za-z0-9-]+\.(?:lan|local|internal|corp)\b"),
    "raw_trace": re.compile(r"Traceback \(most recent call last\)|File \"/home/[A-Za-z0-9._/-]+\", line \d+"),
}

ALLOW_LINE_TOKENS = {
    "example.com",
    "example.org",
    "example.net",
    "111122223333",
    "123456789012",
    "A[K]IA",
}


@dataclass(frozen=True)
class Issue:
    location: str
    message: str

    def render(self) -> str:
        return f"{self.location}: {self.message}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate JSON/JSONL datasets against a Draft 2020-12 JSON Schema plus public-safety checks."
    )
    parser.add_argument("--schema", required=True, type=Path, help="Path to a Draft 2020-12 JSON Schema file.")
    parser.add_argument("--input", required=True, type=Path, help="JSON or JSONL file to validate.")
    parser.add_argument(
        "--format",
        choices=("auto", "json", "jsonl"),
        default="auto",
        help="Input format. Defaults to JSONL for .jsonl files and JSON otherwise.",
    )
    parser.add_argument(
        "--skip-public-safety",
        action="store_true",
        help="Only validate schema shape. Intended for local debugging, not CI gates.",
    )
    return parser.parse_args()


def resolve_format(path: Path, requested: str) -> str:
    if requested != "auto":
        return requested
    return "jsonl" if path.suffix == ".jsonl" else "json"


def load_schema(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"schema is invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("schema root must be a JSON object")
    try:
        Draft202012Validator.check_schema(payload)
    except SchemaError as exc:
        raise ValueError(f"schema is not a valid Draft 2020-12 schema: {exc.message}") from exc
    return payload


def load_json(path: Path) -> Iterable[tuple[str, Any, str]]:
    text = path.read_text(encoding="utf-8")
    try:
        yield path.name, json.loads(text), text
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc


def load_jsonl(path: Path) -> Iterable[tuple[str, Any, str]]:
    rows = 0
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        rows += 1
        try:
            yield f"line {line_no}", json.loads(line), line
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_no}: invalid JSON at column {exc.colno}: {exc.msg}") from exc
    if rows == 0:
        raise ValueError("input contains no JSON objects")


def schema_issue(location: str, exc: ValidationError) -> Issue:
    path = ""
    if exc.absolute_path:
        path = "." + ".".join(str(part) for part in exc.absolute_path)
    return Issue(location=f"{location}{path}", message=exc.message)


def safety_issues(location: str, text: str) -> list[Issue]:
    issues: list[Issue] = []
    if any(token in text for token in ALLOW_LINE_TOKENS):
        return issues
    for name, pattern in PUBLIC_SAFETY_PATTERNS.items():
        if pattern.search(text):
            issues.append(Issue(location=location, message=f"public-safety violation: {name}"))
    return issues


def validate_rows(schema: dict[str, Any], rows: Iterable[tuple[str, Any, str]], *, public_safety: bool) -> tuple[int, list[Issue]]:
    validator = Draft202012Validator(schema)
    issues: list[Issue] = []
    count = 0
    for location, payload, raw_text in rows:
        count += 1
        for exc in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path)):
            issues.append(schema_issue(location, exc))
        if public_safety:
            issues.extend(safety_issues(location, raw_text))
    return count, issues


def main() -> int:
    args = parse_args()
    schema_path = args.schema.resolve()
    input_path = args.input.resolve()
    input_format = resolve_format(input_path, args.format)

    try:
        schema = load_schema(schema_path)
        rows = load_jsonl(input_path) if input_format == "jsonl" else load_json(input_path)
        count, issues = validate_rows(schema, rows, public_safety=not args.skip_public_safety)
    except Exception as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1

    if issues:
        print("validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue.render()}", file=sys.stderr)
        return 1

    print(json.dumps({"valid": True, "format": input_format, "rows": count, "schema": str(schema_path.relative_to(ROOT) if schema_path.is_relative_to(ROOT) else schema_path), "input": str(input_path.relative_to(ROOT) if input_path.is_relative_to(ROOT) else input_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
