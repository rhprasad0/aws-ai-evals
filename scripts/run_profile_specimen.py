#!/usr/bin/env python3
"""Run the profile-only specimen over eval-example rows in local stub mode."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
except Exception as exc:  # pragma: no cover - dependency failure path
    raise SystemExit("Missing dependency: install jsonschema to run the specimen runner") from exc

try:
    import profile_specimen
except ModuleNotFoundError:  # pragma: no cover - import path used by tests
    from scripts import profile_specimen  # type: ignore[no-redef]

DEFAULT_DATASET = Path("datasets/synthetic/recruiter-evidence-qa.jsonl")
DEFAULT_PROFILE = Path("profile.md")
DEFAULT_OUTPUT_DIR = Path("build/captured-responses")
CAPTURED_RESPONSE_SCHEMA = Path("schemas/captured-response.schema.json")


def default_run_id(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y%m%d%H%M%S")
    return f"local-stub-{timestamp}"


def select_examples(
    rows: list[dict[str, Any]],
    *,
    example_ids: list[str] | None = None,
    production_probes: bool = False,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    selected = rows
    if example_ids:
        wanted = set(example_ids)
        selected = [row for row in selected if row.get("exampleId") in wanted]
        found = {str(row.get("exampleId")) for row in selected}
        missing = sorted(wanted - found)
        if missing:
            raise ValueError(f"exampleId not found: {', '.join(missing)}")
    if production_probes:
        selected = [row for row in selected if row.get("productionAiProbe") is True]
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be at least 1")
        selected = selected[:limit]
    if not selected:
        raise ValueError("no examples selected")
    return selected


def stub_response_for_example(example: dict[str, Any]) -> dict[str, str]:
    expected_behavior = example.get("expectedBehavior")
    request_class = example.get("requestClass")
    if request_class == "off_topic_or_abuse" or expected_behavior == "refuse_or_redirect":
        return {
            "answer": "I can only answer recruiter-facing questions using profile.md, so I cannot help with that request.",
            "responseKind": "refusal",
        }
    if expected_behavior == "say_not_supported":
        return {
            "answer": "profile.md does not support that claim. It supports adjacent public evidence around AI evaluation, AWS implementation, agent orchestration, and production-relevant engineering practices.",
            "responseKind": "not_supported",
        }
    if expected_behavior == "answer_with_caveat" or example.get("productionAiProbe") is True:
        return {
            "answer": "The profile does not support claiming production AI ownership. It does support production-relevant adjacent evidence: eval design, AWS implementation, orchestration, security boundaries, observability, and runbook-style documentation.",
            "responseKind": "caveat",
        }
    return {
        "answer": "profile.md contains public project evidence relevant to this question. A live model call will produce the final answer in a later slice.",
        "responseKind": "answer",
    }


def load_captured_response_validator(root: Path) -> Draft202012Validator:
    schema = json.loads((root / CAPTURED_RESPONSE_SCHEMA).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_records(records: list[dict[str, Any]], validator: Draft202012Validator) -> list[str]:
    messages: list[str] = []
    for index, record in enumerate(records, start=1):
        for error in sorted(validator.iter_errors(record), key=lambda item: (list(item.path), list(item.schema_path))):
            path = "$" + "".join(f".{part}" if not isinstance(part, int) else f"[{part}]" for part in error.path)
            messages.append(f"record {index} ({record.get('exampleId', 'unknown')}): {error.message} at {path}")
    return messages


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(record, separators=(",", ":")) for record in records) + "\n"
    path.write_text(payload, encoding="utf-8")


def run_stub_capture(
    *,
    root: Path,
    dataset_path: Path,
    profile_path: Path,
    output_path: Path,
    run_id: str,
    example_ids: list[str] | None = None,
    production_probes: bool = False,
    limit: int | None = None,
    captured_at: datetime | None = None,
) -> list[dict[str, Any]]:
    rows = profile_specimen.load_jsonl(dataset_path)
    selected = select_examples(rows, example_ids=example_ids, production_probes=production_probes, limit=limit)
    profile_text = profile_path.read_text(encoding="utf-8")
    timestamp = captured_at or datetime.now(UTC)
    records = [
        profile_specimen.captured_response_record(
            profile_specimen.input_from_example(example),
            stub_response_for_example(example),
            run_id=run_id,
            model_id=profile_specimen.DEFAULT_MODEL_ID,
            profile_text=profile_text,
            captured_at=timestamp,
        )
        for example in selected
    ]
    validation_messages = validate_records(records, load_captured_response_validator(root))
    if validation_messages:
        raise ValueError("captured response validation failed:\n" + "\n".join(validation_messages))
    write_jsonl(output_path, records)
    return records


def resolve_path(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the profile-only specimen over dataset rows in local stub mode.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, help="Captured-response JSONL output path")
    parser.add_argument("--run-id", default=default_run_id())
    parser.add_argument("--example-id", action="append", dest="example_ids", help="Run a specific exampleId; can be repeated")
    parser.add_argument("--production-probes", action="store_true", help="Run only production AI probe rows")
    parser.add_argument("--limit", type=int, help="Limit selected rows after filtering")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    output = args.output or DEFAULT_OUTPUT_DIR / f"{args.run_id}.jsonl"
    output_path = resolve_path(root, output)
    records = run_stub_capture(
        root=root,
        dataset_path=resolve_path(root, args.dataset),
        profile_path=resolve_path(root, args.profile),
        output_path=output_path,
        run_id=args.run_id,
        example_ids=args.example_ids,
        production_probes=args.production_probes,
        limit=args.limit,
    )
    try:
        display_output = output_path.relative_to(root)
    except ValueError:
        display_output = output_path
    print(f"OK: wrote {len(records)} captured response(s) to {display_output}")
    print(f"OK: validated against {CAPTURED_RESPONSE_SCHEMA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
