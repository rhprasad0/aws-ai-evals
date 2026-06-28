#!/usr/bin/env python3
"""Run the profile-only specimen over eval-example rows."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
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
DEFAULT_BEDROCK_MODEL_ID = "us.amazon.nova-2-lite-v1:0"
DEFAULT_REGION = "us-east-1"


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


def create_bedrock_client(region: str):
    try:
        import boto3
        from botocore.config import Config
    except Exception:
        boto3 = None
        Config = None
    if boto3 is not None and Config is not None:
        client = boto3.client("bedrock-runtime", region_name=region, config=Config(read_timeout=120))
        if hasattr(client, "converse"):
            return client
    if shutil.which("aws"):
        return AwsCliBedrockClient(region)
    raise SystemExit("Bedrock live mode requires boto3 with Converse support or AWS CLI v2")


class AwsCliBedrockClient:
    def __init__(self, region: str) -> None:
        self.region = region

    def converse(self, **kwargs):
        command = [
            "aws",
            "bedrock-runtime",
            "converse",
            "--region",
            self.region,
            "--model-id",
            kwargs["modelId"],
            "--messages",
            json.dumps(kwargs["messages"], separators=(",", ":")),
            "--inference-config",
            json.dumps(kwargs["inferenceConfig"], separators=(",", ":")),
        ]
        completed = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return json.loads(completed.stdout)


def extract_converse_text(response: dict[str, Any]) -> str:
    content = response.get("output", {}).get("message", {}).get("content", [])
    texts = [block["text"] for block in content if isinstance(block, dict) and isinstance(block.get("text"), str)]
    if not texts:
        raise ValueError("Bedrock Converse response did not include text content")
    return "\n".join(texts).strip()


def bedrock_response_for_example(
    example: dict[str, Any],
    *,
    profile_text: str,
    client: Any,
    model_id: str,
    max_tokens: int,
    temperature: float,
    top_p: float,
) -> dict[str, str]:
    specimen_input = profile_specimen.input_from_example(example)
    prompt = profile_specimen.build_prompt(specimen_input, profile_text)
    response = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature, "topP": top_p},
    )
    return profile_specimen.normalize_model_response(extract_converse_text(response))


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


def run_capture(
    *,
    root: Path,
    dataset_path: Path,
    profile_path: Path,
    output_path: Path,
    run_id: str,
    mode: str = "stub",
    model_id: str = profile_specimen.DEFAULT_MODEL_ID,
    region: str = DEFAULT_REGION,
    max_tokens: int = 700,
    temperature: float = 0.0,
    top_p: float = 0.9,
    example_ids: list[str] | None = None,
    production_probes: bool = False,
    limit: int | None = None,
    captured_at: datetime | None = None,
    bedrock_client: Any | None = None,
) -> list[dict[str, Any]]:
    rows = profile_specimen.load_jsonl(dataset_path)
    selected = select_examples(rows, example_ids=example_ids, production_probes=production_probes, limit=limit)
    profile_text = profile_path.read_text(encoding="utf-8")
    timestamp = captured_at or datetime.now(UTC)
    client = bedrock_client or (create_bedrock_client(region) if mode == "bedrock" else None)
    records = []
    for example in selected:
        response = (
            bedrock_response_for_example(
                example,
                profile_text=profile_text,
                client=client,
                model_id=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            if mode == "bedrock"
            else stub_response_for_example(example)
        )
        records.append(
            profile_specimen.captured_response_record(
                profile_specimen.input_from_example(example),
                response,
                run_id=run_id,
                model_id=model_id,
                profile_text=profile_text,
                captured_at=timestamp,
            )
        )
    validation_messages = validate_records(records, load_captured_response_validator(root))
    if validation_messages:
        raise ValueError("captured response validation failed:\n" + "\n".join(validation_messages))
    write_jsonl(output_path, records)
    return records


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
    return run_capture(
        root=root,
        dataset_path=dataset_path,
        profile_path=profile_path,
        output_path=output_path,
        run_id=run_id,
        mode="stub",
        model_id=profile_specimen.DEFAULT_MODEL_ID,
        example_ids=example_ids,
        production_probes=production_probes,
        limit=limit,
        captured_at=captured_at,
    )


def resolve_path(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the profile-only specimen over dataset rows.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, help="Captured-response JSONL output path")
    parser.add_argument("--run-id", default=default_run_id())
    parser.add_argument("--mode", choices=["stub", "bedrock"], default="stub")
    parser.add_argument("--model-id", help="Generator model id; defaults to stub-local in stub mode and Nova Lite in Bedrock mode")
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--example-id", action="append", dest="example_ids", help="Run a specific exampleId; can be repeated")
    parser.add_argument("--production-probes", action="store_true", help="Run only production AI probe rows")
    parser.add_argument("--limit", type=int, help="Limit selected rows after filtering")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    model_id = args.model_id or (DEFAULT_BEDROCK_MODEL_ID if args.mode == "bedrock" else profile_specimen.DEFAULT_MODEL_ID)
    output = args.output or DEFAULT_OUTPUT_DIR / f"{args.run_id}.jsonl"
    output_path = resolve_path(root, output)
    records = run_capture(
        root=root,
        dataset_path=resolve_path(root, args.dataset),
        profile_path=resolve_path(root, args.profile),
        output_path=output_path,
        run_id=args.run_id,
        mode=args.mode,
        model_id=model_id,
        region=args.region,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        top_p=args.top_p,
        example_ids=args.example_ids,
        production_probes=args.production_probes,
        limit=args.limit,
    )
    try:
        display_output = output_path.relative_to(root)
    except ValueError:
        display_output = output_path
    print(f"OK: wrote {len(records)} captured response(s) to {display_output}")
    print(f"OK: mode={args.mode} modelId={model_id}")
    print(f"OK: validated against {CAPTURED_RESPONSE_SCHEMA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
