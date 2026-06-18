#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - dependency guard for fresh machines
    raise SystemExit("export failed: install jsonschema to use scripts/export_chat_app_events.py") from exc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_GROUP = "/aws/lambda/rp-chatbot-chat"
DEFAULT_SCHEMA = ROOT / "schemas" / "aws-evals" / "normalized-app-event.schema.json"


class ExportError(ValueError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export safe CloudWatch chat_app_event log records to normalized schema-valid JSONL."
    )
    source = parser.add_mutually_exclusive_group(required=False)
    source.add_argument(
        "--input",
        type=Path,
        help="Optional JSON file from aws logs filter-log-events. Omit to query CloudWatch directly.",
    )
    source.add_argument(
        "--stdin",
        action="store_true",
        help="Read aws logs filter-log-events JSON from stdin.",
    )
    parser.add_argument("--log-group-name", default=DEFAULT_LOG_GROUP)
    parser.add_argument("--since-minutes", type=int, default=60, help="Direct CloudWatch mode start window.")
    parser.add_argument("--start-time-ms", type=int, help="Direct CloudWatch mode explicit start time in epoch ms.")
    parser.add_argument("--end-time-ms", type=int, help="Direct CloudWatch mode explicit end time in epoch ms.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum events to request in direct CloudWatch mode.")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output", required=True, type=Path, help="Normalized JSONL output path.")
    parser.add_argument(
        "--s3-uri",
        help="Optional s3:// bucket/prefix/key destination. Uses aws s3 cp after local JSONL validation succeeds.",
    )
    return parser.parse_args()


def load_schema(path: Path) -> dict[str, Any]:
    schema = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise ExportError("schema root must be a JSON object")
    Draft202012Validator.check_schema(schema)
    return schema


def load_filter_events_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.stdin:
        raw = sys.stdin.read()
    elif args.input:
        raw = args.input.read_text(encoding="utf-8")
    else:
        raw = query_cloudwatch_events(args)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExportError(f"input is not valid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ExportError("input must be a JSON object from aws logs filter-log-events")
    return payload


def query_cloudwatch_events(args: argparse.Namespace) -> str:
    end_ms = args.end_time_ms or int(time.time() * 1000)
    start_ms = args.start_time_ms or end_ms - (args.since_minutes * 60 * 1000)
    if start_ms >= end_ms:
        raise ExportError("start time must be earlier than end time")
    command = [
        "aws",
        "logs",
        "filter-log-events",
        "--log-group-name",
        args.log_group_name,
        "--start-time",
        str(start_ms),
        "--end-time",
        str(end_ms),
        "--filter-pattern",
        "chat_app_event",
        "--limit",
        str(args.limit),
        "--output",
        "json",
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise ExportError(result.stderr.strip() or "aws logs filter-log-events failed")
    return result.stdout


def extract_event_payload(message: str) -> dict[str, Any] | None:
    marker = "chat_app_event "
    if marker not in message:
        return None
    event_text = message.split(marker, 1)[1].strip()
    try:
        payload = json.loads(event_text)
    except json.JSONDecodeError as exc:
        raise ExportError(f"chat_app_event payload is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ExportError("chat_app_event payload must be a JSON object")
    normalized = {"schema_version": "normalized-app-event/v1", **payload}
    return normalized


def iter_normalized_events(filter_events_payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    events = filter_events_payload.get("events", [])
    if not isinstance(events, list):
        raise ExportError("input .events must be a list")
    for event in events:
        if not isinstance(event, dict):
            continue
        message = event.get("message")
        if not isinstance(message, str):
            continue
        normalized = extract_event_payload(message)
        if normalized is not None:
            yield normalized


def validate_events(events: list[dict[str, Any]], schema: dict[str, Any]) -> None:
    if not events:
        raise ExportError("no chat_app_event records found")
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for index, event in enumerate(events, 1):
        for exc in sorted(validator.iter_errors(event), key=lambda item: list(item.absolute_path)):
            path = "." + ".".join(str(part) for part in exc.absolute_path) if exc.absolute_path else ""
            errors.append(f"event {index}{path}: {exc.message}")
    if errors:
        raise ExportError("schema validation failed:\n- " + "\n- ".join(errors))


def write_jsonl(path: Path, events: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")


def upload_to_s3(output: Path, s3_uri: str) -> None:
    if not s3_uri.startswith("s3://"):
        raise ExportError("--s3-uri must start with s3://")
    result = subprocess.run(["aws", "s3", "cp", str(output), s3_uri], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise ExportError(result.stderr.strip() or "aws s3 cp failed")


def summarize(events: list[dict[str, Any]], output: Path, s3_uri: str | None) -> dict[str, Any]:
    return {
        "events": len(events),
        "output": str(output),
        "s3_uri": s3_uri,
        "response_sources": sorted({event["response_source"] for event in events}),
        "evidence_strengths": sorted({event["evidence_strength"] for event in events}),
    }


def main() -> int:
    args = parse_args()
    try:
        schema = load_schema(args.schema)
        payload = load_filter_events_payload(args)
        events = list(iter_normalized_events(payload))
        validate_events(events, schema)
        write_jsonl(args.output, events)
        if args.s3_uri:
            upload_to_s3(args.output, args.s3_uri)
    except Exception as exc:
        print(f"export failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summarize(events, args.output, args.s3_uri), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
