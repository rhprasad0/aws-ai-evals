#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUBRICS_DIR = ROOT / "rubrics"
DEFAULT_OUTPUT_DIR = ROOT / "build" / "bedrock-custom-metrics"

METRIC_NAMES = {
    "correctness": "CustomMetric-CandidateCorrectness",
    "completeness": "CustomMetric-CandidateCompleteness",
    "citation-support": "CustomMetric-CandidateCitationSupport",
    "refusal-appropriateness": "CustomMetric-CandidateRefusalAppropriateness",
    "evidence-strength-calibration": "CustomMetric-CandidateEvidenceStrengthCalibration",
}

BEDROCK_INPUT_BLOCK = """
Input variables:
- User prompt: {{prompt}}
- Candidate response to evaluate: {{prediction}}
- Reference answer / expected behavior: {{ground_truth}}

Return the rating selected from the configured rating scale. Do not include private data, raw traces, or unrequested source text in the rationale.
""".strip()


@dataclass(frozen=True)
class RubricMetric:
    slug: str
    metric_name: str
    instructions: str
    rating_scale: list[dict[str, Any]]

    def to_bedrock_definition(self) -> dict[str, Any]:
        return {
            "customMetricDefinition": {
                "name": self.metric_name,
                "instructions": self.instructions,
                "ratingScale": self.rating_scale,
            }
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Bedrock custom metric JSON definitions from Week 5 rubric markdown files.")
    parser.add_argument("--rubrics-dir", type=Path, default=DEFAULT_RUBRICS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--combined-file", default="custom-metrics.json", help="Combined output filename written inside output-dir.")
    return parser.parse_args()


def section(markdown: str, heading: str) -> str:
    pattern = re.compile(rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(markdown)
    if not match:
        raise ValueError(f"missing section: {heading}")
    return match.group("body").strip()


def first_heading(markdown: str) -> str:
    match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    if not match:
        raise ValueError("missing title heading")
    return match.group(1).strip()


def parse_rating_scale(markdown: str) -> list[dict[str, Any]]:
    body = section(markdown, "Allowed scores")
    rows: list[dict[str, Any]] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped or "Score" in stripped:
            continue
        columns = [column.strip() for column in stripped.strip("|").split("|")]
        if len(columns) < 3:
            continue
        try:
            score = int(columns[0])
        except ValueError:
            continue
        definition = columns[1]
        rows.append({"definition": definition, "value": {"floatValue": score}})
    scores = {row["value"]["floatValue"] for row in rows}
    if scores != {0, 1, 2}:
        raise ValueError(f"rating scale must contain scores 0, 1, 2; got {sorted(scores)}")
    return sorted(rows, key=lambda row: row["value"]["floatValue"])


def build_instructions(markdown: str) -> str:
    title = first_heading(markdown)
    purpose = section(markdown, "Purpose")
    judge_instructions = section(markdown, "Judge instructions")
    good_example = section(markdown, "Good judgment example")
    bad_example = section(markdown, "Bad judgment example")
    return "\n\n".join(
        [
            f"You are evaluating a candidate evidence chatbot response using the {title}.",
            "Purpose:\n" + purpose,
            "Evaluation instructions:\n" + judge_instructions,
            "Good judgment example:\n" + good_example,
            "Bad judgment example:\n" + bad_example,
            BEDROCK_INPUT_BLOCK,
        ]
    )


def metric_from_rubric(path: Path) -> RubricMetric:
    slug = path.stem
    metric_name = METRIC_NAMES.get(slug)
    if metric_name is None:
        raise ValueError(f"no Bedrock metric name configured for rubric slug: {slug}")
    markdown = path.read_text(encoding="utf-8")
    return RubricMetric(
        slug=slug,
        metric_name=metric_name,
        instructions=build_instructions(markdown),
        rating_scale=parse_rating_scale(markdown),
    )


def build_metrics(rubrics_dir: Path) -> list[RubricMetric]:
    paths = sorted(rubrics_dir.glob("*.md"))
    if not paths:
        raise ValueError(f"no rubric markdown files found in {rubrics_dir}")
    metrics = [metric_from_rubric(path) for path in paths]
    expected = set(METRIC_NAMES)
    actual = {metric.slug for metric in metrics}
    missing = sorted(expected - actual)
    if missing:
        raise ValueError(f"missing rubric files for: {missing}")
    return sorted(metrics, key=lambda metric: metric.metric_name)


def write_outputs(metrics: list[RubricMetric], output_dir: Path, combined_file: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    combined = []
    for metric in metrics:
        payload = metric.to_bedrock_definition()
        combined.append(payload)
        path = output_dir / f"{metric.slug}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    combined_path = output_dir / combined_file
    combined_path.write_text(json.dumps({"customMetrics": combined}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written.append(combined_path)
    return written


def main() -> int:
    args = parse_args()
    try:
        metrics = build_metrics(args.rubrics_dir)
        written = write_outputs(metrics, args.output_dir, args.combined_file)
    except Exception as exc:
        print(f"custom metric build failed: {exc}", flush=True)
        return 1
    print(json.dumps({"metrics": [metric.metric_name for metric in metrics], "written": [str(path) for path in written]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
