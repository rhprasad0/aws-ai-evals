#!/usr/bin/env python3
"""Local eval harness for mechanical joins and summary reports."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
except Exception as exc:  # pragma: no cover - dependency failure path
    raise SystemExit("Missing dependency: install jsonschema to run eval harness") from exc

try:
    from scripts import validate_dataset
except ImportError:  # pragma: no cover - script execution path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import validate_dataset  # type: ignore[no-redef]


DEFAULT_EXAMPLES = Path("datasets/synthetic/recruiter-evidence-qa.jsonl")
DEFAULT_RESPONSES = Path("tests/fixtures/captured-responses/live-smoke-reviewed.jsonl")
DEFAULT_LABELS = Path("tests/fixtures/human-labels/live-smoke-reviewed.jsonl")

SCHEMA_FOR_KIND = {
    "examples": "eval-example",
    "responses": "captured-response",
    "labels": "human-label",
}


@dataclass(frozen=True)
class HarnessFailure:
    message: str


@dataclass(frozen=True)
class HarnessResult:
    summary: dict[str, Any]
    failures: list[HarnessFailure]

    @property
    def ok(self) -> bool:
        return not self.failures


def resolve_path(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def load_validator(root: Path, schema_name: str) -> Draft202012Validator:
    schema, failures = validate_dataset.load_schema(root, schema_name)
    if failures or schema is None:
        rendered = "\n".join(failure.render(root) for failure in failures)
        raise ValueError(f"failed to load schema {schema_name}:\n{rendered}")
    return Draft202012Validator(schema, format_checker=FormatChecker())


def load_validated_jsonl(root: Path, path: Path, schema_name: str) -> tuple[list[dict[str, Any]], list[HarnessFailure]]:
    validator = load_validator(root, schema_name)
    row_count, validation_failures = validate_dataset.validate_jsonl_file(path, validator)
    failures = [HarnessFailure(failure.render(root)) for failure in validation_failures]
    if failures:
        return [], failures
    rows, load_failures = validate_dataset.load_jsonl(path)
    failures.extend(HarnessFailure(failure.render(root)) for failure in load_failures)
    if len(rows) != row_count:
        failures.append(HarnessFailure(f"{path}: loaded row count did not match validated row count"))
    return rows, failures


def index_by_example_id(kind: str, rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[HarnessFailure]]:
    indexed: dict[str, dict[str, Any]] = {}
    failures: list[HarnessFailure] = []
    for row in rows:
        example_id = row.get("exampleId")
        if not isinstance(example_id, str):
            failures.append(HarnessFailure(f"{kind}: row missing string exampleId"))
            continue
        if example_id in indexed:
            failures.append(HarnessFailure(f"{kind}: duplicate exampleId {example_id!r}"))
            continue
        indexed[example_id] = row
    return indexed, failures


def count_labels(labels: list[dict[str, Any]]) -> tuple[Counter[str], Counter[str]]:
    outcomes: Counter[str] = Counter()
    failure_tags: Counter[str] = Counter()
    for label in labels:
        outcome = label.get("humanOutcome")
        if isinstance(outcome, str):
            outcomes[outcome] += 1
        for tag in label.get("failureTags", []) or []:
            if isinstance(tag, str):
                failure_tags[tag] += 1
    return outcomes, failure_tags


def build_summary(
    examples: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    labels: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[HarnessFailure]]:
    failures: list[HarnessFailure] = []
    examples_by_id, index_failures = index_by_example_id("examples", examples)
    failures.extend(index_failures)
    responses_by_id, index_failures = index_by_example_id("responses", responses)
    failures.extend(index_failures)
    labels_by_id, index_failures = index_by_example_id("labels", labels)
    failures.extend(index_failures)

    example_ids = set(examples_by_id)
    response_ids = set(responses_by_id)
    label_ids = set(labels_by_id)

    missing_response_ids = sorted(example_ids - response_ids)
    missing_label_ids = sorted(example_ids - label_ids)
    orphan_response_ids = sorted(response_ids - example_ids)
    orphan_label_ids = sorted(label_ids - example_ids)

    for response in responses:
        if not isinstance(response.get("response", {}).get("answer"), str) or not response["response"].get("answer"):
            failures.append(HarnessFailure(f"responses: {response.get('exampleId', '<unknown>')} missing response.answer"))
    for label in labels:
        label_example_id = label.get("exampleId")
        response = responses_by_id.get(label_example_id) if isinstance(label_example_id, str) else None
        if response and label.get("runId") != response.get("runId"):
            failures.append(
                HarnessFailure(
                    f"labels: {label_example_id} runId {label.get('runId')!r} does not match response runId {response.get('runId')!r}"
                )
            )

    outcomes, failure_tags = count_labels(labels)
    production_probe_ids = {row["exampleId"] for row in examples if row.get("productionAiProbe") is True}
    production_labeled = [labels_by_id[example_id] for example_id in sorted(production_probe_ids & label_ids)]
    production_outcomes, _ = count_labels(production_labeled)

    summary = {
        "totalExamples": len(examples),
        "capturedResponses": len(responses),
        "humanLabels": len(labels),
        "labeledResponses": len(response_ids & label_ids & example_ids),
        "outcomes": {"pass": outcomes.get("pass", 0), "fail": outcomes.get("fail", 0)},
        "failureTags": dict(sorted(failure_tags.items())),
        "productionAiProbes": {
            "total": len(production_probe_ids),
            "withResponse": len(production_probe_ids & response_ids),
            "withLabel": len(production_probe_ids & label_ids),
            "pass": production_outcomes.get("pass", 0),
            "fail": production_outcomes.get("fail", 0),
        },
        "missingResponses": {"count": len(missing_response_ids), "exampleIds": missing_response_ids},
        "missingLabels": {"count": len(missing_label_ids), "exampleIds": missing_label_ids},
        "orphanResponses": {"count": len(orphan_response_ids), "exampleIds": orphan_response_ids},
        "orphanLabels": {"count": len(orphan_label_ids), "exampleIds": orphan_label_ids},
    }
    return summary, failures


def run_harness(root: Path, examples_path: Path, responses_path: Path, labels_path: Path) -> HarnessResult:
    examples, failures = load_validated_jsonl(root, examples_path, SCHEMA_FOR_KIND["examples"])
    all_failures = list(failures)
    responses, failures = load_validated_jsonl(root, responses_path, SCHEMA_FOR_KIND["responses"])
    all_failures.extend(failures)
    labels, failures = load_validated_jsonl(root, labels_path, SCHEMA_FOR_KIND["labels"])
    all_failures.extend(failures)
    if all_failures:
        return HarnessResult(summary={}, failures=all_failures)
    summary, join_failures = build_summary(examples, responses, labels)
    return HarnessResult(summary=summary, failures=join_failures)


def render_text(summary: dict[str, Any]) -> str:
    lines = [
        "Local eval harness summary",
        "==========================",
        f"examples: {summary['totalExamples']}",
        f"captured responses: {summary['capturedResponses']}",
        f"human labels: {summary['humanLabels']}",
        f"labeled responses: {summary['labeledResponses']}",
        f"pass: {summary['outcomes']['pass']}",
        f"fail: {summary['outcomes']['fail']}",
    ]
    failure_tags = summary["failureTags"] or {}
    lines.append("failure tags: " + (", ".join(f"{tag}={count}" for tag, count in failure_tags.items()) if failure_tags else "none"))
    production = summary["productionAiProbes"]
    lines.extend(
        [
            "production AI probes: "
            f"total={production['total']} response={production['withResponse']} label={production['withLabel']} "
            f"pass={production['pass']} fail={production['fail']}",
            f"missing responses: {summary['missingResponses']['count']}",
            f"missing labels: {summary['missingLabels']['count']}",
            f"orphan responses: {summary['orphanResponses']['count']}",
            f"orphan labels: {summary['orphanLabels']['count']}",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and summarize local eval examples, captured responses, and human labels.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root")
    parser.add_argument("--examples", type=Path, default=DEFAULT_EXAMPLES)
    parser.add_argument("--responses", type=Path, default=DEFAULT_RESPONSES)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    result = run_harness(
        root,
        resolve_path(root, args.examples),
        resolve_path(root, args.responses),
        resolve_path(root, args.labels),
    )
    if result.failures:
        print(f"FAIL: {len(result.failures)} harness issue(s)", file=sys.stderr)
        for failure in result.failures:
            print(failure.message, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result.summary, indent=2, sort_keys=True))
    else:
        print(render_text(result.summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
