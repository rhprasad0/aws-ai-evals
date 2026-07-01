#!/usr/bin/env python3
"""Validate local eval schemas, fixtures, and JSONL datasets."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
except Exception as exc:  # pragma: no cover - dependency failure path
    raise SystemExit("Missing dependency: install jsonschema to run dataset validation") from exc


@dataclass(frozen=True)
class ValidationFailure:
    path: Path
    message: str
    line: int | None = None
    json_path: str | None = None
    schema_path: str | None = None

    def render(self, root: Path) -> str:
        try:
            display_path = self.path.relative_to(root)
        except ValueError:
            display_path = self.path
        location = str(display_path)
        if self.line is not None:
            location += f":{self.line}"
        details = [self.message]
        if self.json_path:
            details.append(f"json_path={self.json_path}")
        if self.schema_path:
            details.append(f"schema_path={self.schema_path}")
        return f"{location}: " + " | ".join(details)


SCHEMA_SPECS = {
    "eval-example": {
        "schema": Path("schemas/eval-example.schema.json"),
        "valid_fixture": Path("tests/fixtures/schemas/eval-example.valid.json"),
        "invalid_fixture": Path("tests/fixtures/schemas/eval-example.invalid.json"),
    },
    "captured-response": {
        "schema": Path("schemas/captured-response.schema.json"),
        "valid_fixture": Path("tests/fixtures/schemas/captured-response.valid.json"),
        "invalid_fixture": Path("tests/fixtures/schemas/captured-response.invalid.json"),
    },
    "human-label": {
        "schema": Path("schemas/human-label.schema.json"),
        "valid_fixture": Path("tests/fixtures/schemas/human-label.valid.json"),
        "invalid_fixture": Path("tests/fixtures/schemas/human-label.invalid.json"),
    },
    "judge-output": {
        "schema": Path("schemas/judge-output.schema.json"),
        "valid_fixture": Path("tests/fixtures/schemas/judge-output.valid.json"),
        "invalid_fixture": Path("tests/fixtures/schemas/judge-output.invalid.json"),
    },
}

DEFAULT_DATASETS = [
    (Path("datasets/synthetic/recruiter-evidence-qa.jsonl"), "eval-example"),
]


def load_json(path: Path) -> tuple[Any | None, list[ValidationFailure]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return None, [ValidationFailure(path, "file not found")]
    except json.JSONDecodeError as exc:
        return None, [ValidationFailure(path, f"invalid JSON: {exc.msg}", line=exc.lineno)]


def load_jsonl(path: Path) -> tuple[list[Any], list[ValidationFailure]]:
    failures: list[ValidationFailure] = []
    values: list[Any] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return [], [ValidationFailure(path, "file not found")]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(ValidationFailure(path, f"invalid JSONL row: {exc.msg}", line=line_number))
            continue
        if not isinstance(value, dict):
            failures.append(ValidationFailure(path, "JSONL row must be an object", line=line_number))
            continue
        values.append(value)
    return values, failures


def json_path(parts: Any) -> str:
    rendered = "$"
    for part in parts:
        if isinstance(part, int):
            rendered += f"[{part}]"
        else:
            rendered += f".{part}"
    return rendered


def schema_path(parts: Any) -> str:
    return "/" + "/".join(str(part) for part in parts)


def display_path(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def schema_errors(path: Path, validator: Draft202012Validator, value: Any, line: int | None = None) -> list[ValidationFailure]:
    failures: list[ValidationFailure] = []
    for error in sorted(validator.iter_errors(value), key=lambda item: (list(item.path), list(item.schema_path))):
        failures.append(
            ValidationFailure(
                path=path,
                line=line,
                message=error.message,
                json_path=json_path(error.path),
                schema_path=schema_path(error.schema_path),
            )
        )
    return failures


def load_schema(root: Path, name: str) -> tuple[dict[str, Any] | None, list[ValidationFailure]]:
    spec = SCHEMA_SPECS[name]
    path = root / spec["schema"]
    value, failures = load_json(path)
    if failures:
        return None, failures
    try:
        Draft202012Validator.check_schema(value)
    except Exception as exc:
        return None, [ValidationFailure(path, f"invalid Draft 2020-12 schema: {exc}")]
    return value, []


def validate_json_file(path: Path, validator: Draft202012Validator) -> list[ValidationFailure]:
    value, failures = load_json(path)
    if failures:
        return failures
    return schema_errors(path, validator, value)


def validate_jsonl_file(path: Path, validator: Draft202012Validator) -> tuple[int, list[ValidationFailure]]:
    rows, failures = load_jsonl(path)
    if not rows and not failures:
        failures.append(ValidationFailure(path, "JSONL dataset must contain at least one object"))
    seen_ids: dict[str, int] = {}
    for line_number, row in enumerate(rows, start=1):
        example_id = row.get("exampleId")
        if isinstance(example_id, str):
            if example_id in seen_ids:
                failures.append(
                    ValidationFailure(
                        path,
                        f"duplicate exampleId {example_id!r}; first seen on line {seen_ids[example_id]}",
                        line=line_number,
                        json_path="$.exampleId",
                    )
                )
            else:
                seen_ids[example_id] = line_number
        failures.extend(schema_errors(path, validator, row, line=line_number))
    return len(rows), failures


def validate_schema_fixtures(root: Path, schemas: dict[str, dict[str, Any]]) -> list[ValidationFailure]:
    failures: list[ValidationFailure] = []
    for name, schema in schemas.items():
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        spec = SCHEMA_SPECS[name]
        valid_path = root / spec["valid_fixture"]
        invalid_path = root / spec["invalid_fixture"]

        valid_failures = validate_json_file(valid_path, validator)
        failures.extend(valid_failures)

        invalid_value, invalid_load_failures = load_json(invalid_path)
        if invalid_load_failures:
            failures.extend(invalid_load_failures)
        elif not schema_errors(invalid_path, validator, invalid_value):
            failures.append(ValidationFailure(invalid_path, "invalid fixture unexpectedly passed schema validation"))
    return failures


def validate_repo(root: Path) -> tuple[list[str], list[ValidationFailure]]:
    messages: list[str] = []
    failures: list[ValidationFailure] = []
    schemas: dict[str, dict[str, Any]] = {}

    for name in SCHEMA_SPECS:
        schema, schema_failures = load_schema(root, name)
        failures.extend(schema_failures)
        if schema is not None:
            schemas[name] = schema
    if failures:
        return messages, failures
    messages.append(f"OK: {len(schemas)} schemas are valid Draft 2020-12 JSON Schemas")

    fixture_failures = validate_schema_fixtures(root, schemas)
    failures.extend(fixture_failures)
    if not fixture_failures:
        messages.append(f"OK: {len(schemas) * 2} schema fixtures behaved as expected")

    for relative_dataset, schema_name in DEFAULT_DATASETS:
        validator = Draft202012Validator(schemas[schema_name], format_checker=FormatChecker())
        row_count, dataset_failures = validate_jsonl_file(root / relative_dataset, validator)
        failures.extend(dataset_failures)
        if not dataset_failures:
            messages.append(f"OK: {row_count} rows validated in {relative_dataset}")
    return messages, failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate eval schemas, fixtures, and JSONL datasets.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root")
    parser.add_argument("--json", nargs=2, metavar=("SCHEMA_NAME", "PATH"), help="Validate one JSON file against a named schema")
    parser.add_argument("--jsonl", nargs=2, metavar=("SCHEMA_NAME", "PATH"), help="Validate one JSONL file against a named schema")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    failures: list[ValidationFailure] = []
    messages: list[str] = []

    if args.json or args.jsonl:
        schema_name, file_path = args.json or args.jsonl
        if schema_name not in SCHEMA_SPECS:
            print(f"Unknown schema name: {schema_name}", file=sys.stderr)
            return 2
        schema, schema_failures = load_schema(root, schema_name)
        failures.extend(schema_failures)
        if schema is not None:
            validator = Draft202012Validator(schema, format_checker=FormatChecker())
            target = Path(file_path)
            if not target.is_absolute():
                target = root / target
            if args.json:
                failures.extend(validate_json_file(target, validator))
                if not failures:
                    messages.append(f"OK: {display_path(target, root)} validated against {schema_name}")
            else:
                row_count, jsonl_failures = validate_jsonl_file(target, validator)
                failures.extend(jsonl_failures)
                if not jsonl_failures:
                    messages.append(f"OK: {row_count} rows validated in {display_path(target, root)}")
    else:
        messages, failures = validate_repo(root)

    for message in messages:
        print(message)
    if failures:
        print(f"FAIL: {len(failures)} validation issue(s)", file=sys.stderr)
        for failure in failures:
            print(failure.render(root), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
