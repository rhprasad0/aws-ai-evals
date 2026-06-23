#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELS = ROOT / "datasets" / "synthetic" / "human-labels.jsonl"
SCORES = (0, 1, 2)


@dataclass(frozen=True)
class JoinedJudgment:
    example_id: str
    rubric_id: str
    run_id: str
    judge_model_id: str
    repetition_index: int
    human_score: int
    judge_score: int
    human_label: str
    judge_label: str
    requires_human_review: bool
    failure_labels: tuple[str, ...]

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.example_id, self.rubric_id, self.judge_model_id, self.run_id)

    @property
    def item_key(self) -> tuple[str, str]:
        return (self.example_id, self.rubric_id)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report judge-vs-human calibration metrics for candidate-chatbot rubrics.")
    parser.add_argument("--human-labels", type=Path, default=DEFAULT_LABELS, help="Human labels JSONL.")
    parser.add_argument("--judge-output", required=True, type=Path, help="Generated judge output JSONL.")
    parser.add_argument("--rubric", action="append", help="Optional rubric_id filter. Repeat for multiple rubrics.")
    parser.add_argument("--judge-model", action="append", help="Optional judge_model_id filter. Repeat for multiple models.")
    parser.add_argument("--high-variance-threshold", type=int, default=1, help="Score range that flags repeated-run variance.")
    parser.add_argument("--fail-on-disagreement", action="store_true", help="Exit non-zero when any judge score disagrees with human labels.")
    return parser.parse_args()


def load_jsonl(path: Path, *, allow_empty: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: line {line_no}: invalid JSON at column {exc.colno}: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"{path}: line {line_no}: row must be a JSON object")
        rows.append(payload)
    if not rows and not allow_empty:
        raise ValueError(f"{path}: contains no JSON objects")
    return rows


def human_label_index(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    labels: dict[tuple[str, str], dict[str, Any]] = {}
    duplicates: list[tuple[str, str]] = []
    for row in rows:
        key = (str(row["example_id"]), str(row["rubric_id"]))
        if key in labels:
            duplicates.append(key)
        labels[key] = row
    if duplicates:
        rendered = ", ".join(f"{example_id}/{rubric_id}" for example_id, rubric_id in duplicates[:5])
        raise ValueError(f"duplicate human labels for {rendered}")
    return labels


def join_rows(
    human_rows: list[dict[str, Any]],
    judge_rows: list[dict[str, Any]],
    *,
    rubric_filter: set[str] | None = None,
    judge_model_filter: set[str] | None = None,
) -> tuple[list[JoinedJudgment], list[dict[str, Any]]]:
    labels = human_label_index(human_rows)
    joined: list[JoinedJudgment] = []
    missing: list[dict[str, Any]] = []
    for judge in judge_rows:
        rubric_id = str(judge["rubric_id"])
        judge_model_id = str(judge["judge_model_id"])
        if rubric_filter and rubric_id not in rubric_filter:
            continue
        if judge_model_filter and judge_model_id not in judge_model_filter:
            continue
        key = (str(judge["example_id"]), rubric_id)
        human = labels.get(key)
        if human is None:
            missing.append({"example_id": key[0], "rubric_id": key[1], "judge_model_id": judge_model_id})
            continue
        joined.append(
            JoinedJudgment(
                example_id=key[0],
                rubric_id=rubric_id,
                run_id=str(judge["run_id"]),
                judge_model_id=judge_model_id,
                repetition_index=int(judge["repetition_index"]),
                human_score=int(human["expected_score"]),
                judge_score=int(judge["score"]),
                human_label=str(human["expected_score_label"]),
                judge_label=str(judge["score_label"]),
                requires_human_review=bool(judge.get("requires_human_review", False)),
                failure_labels=tuple(str(label) for label in judge.get("failure_labels", [])),
            )
        )
    return joined, missing


def accuracy(items: list[JoinedJudgment]) -> float | None:
    if not items:
        return None
    return sum(item.human_score == item.judge_score for item in items) / len(items)


def confusion_matrix(items: list[JoinedJudgment]) -> dict[str, dict[str, int]]:
    matrix = {str(human): {str(judge): 0 for judge in SCORES} for human in SCORES}
    for item in items:
        matrix[str(item.human_score)][str(item.judge_score)] += 1
    return matrix


def cohen_kappa(items: list[JoinedJudgment]) -> float | None:
    if not items:
        return None
    total = len(items)
    observed = sum(item.human_score == item.judge_score for item in items) / total
    human_counts = Counter(item.human_score for item in items)
    judge_counts = Counter(item.judge_score for item in items)
    expected = sum((human_counts[score] / total) * (judge_counts[score] / total) for score in SCORES)
    if expected == 1:
        return 1.0 if observed == 1 else None
    return (observed - expected) / (1 - expected)


def group_by(items: Iterable[JoinedJudgment], key_name: str) -> dict[str, list[JoinedJudgment]]:
    groups: dict[str, list[JoinedJudgment]] = defaultdict(list)
    for item in items:
        groups[str(getattr(item, key_name))].append(item)
    return dict(sorted(groups.items()))


def repeated_run_variance(items: list[JoinedJudgment], *, threshold: int) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[JoinedJudgment]] = defaultdict(list)
    for item in items:
        groups[item.key].append(item)
    cases: list[dict[str, Any]] = []
    for (example_id, rubric_id, judge_model_id, run_id), group in sorted(groups.items()):
        if len(group) < 2:
            continue
        scores = [item.judge_score for item in group]
        score_range = max(scores) - min(scores)
        if score_range >= threshold:
            cases.append(
                {
                    "example_id": example_id,
                    "rubric_id": rubric_id,
                    "judge_model_id": judge_model_id,
                    "run_id": run_id,
                    "repetitions": len(group),
                    "scores": scores,
                    "score_range": score_range,
                    "human_score": group[0].human_score,
                }
            )
    return cases


def disagreement_examples(items: list[JoinedJudgment], *, limit: int = 20) -> list[dict[str, Any]]:
    rows = [item for item in items if item.human_score != item.judge_score]
    return [
        {
            "example_id": item.example_id,
            "rubric_id": item.rubric_id,
            "judge_model_id": item.judge_model_id,
            "run_id": item.run_id,
            "repetition_index": item.repetition_index,
            "human_score": item.human_score,
            "judge_score": item.judge_score,
            "failure_labels": list(item.failure_labels),
            "requires_human_review": item.requires_human_review,
        }
        for item in rows[:limit]
    ]


def summarize(items: list[JoinedJudgment], *, missing_labels: list[dict[str, Any]], high_variance_threshold: int) -> dict[str, Any]:
    by_rubric = {
        rubric: {
            "rows": len(group),
            "agreement": accuracy(group),
            "kappa": cohen_kappa(group),
            "confusion_matrix": confusion_matrix(group),
        }
        for rubric, group in group_by(items, "rubric_id").items()
    }
    by_model = {
        model: {
            "rows": len(group),
            "agreement": accuracy(group),
            "kappa": cohen_kappa(group),
        }
        for model, group in group_by(items, "judge_model_id").items()
    }
    high_variance = repeated_run_variance(items, threshold=high_variance_threshold)
    return {
        "rows_joined": len(items),
        "missing_human_labels": missing_labels,
        "overall": {
            "agreement": accuracy(items),
            "kappa": cohen_kappa(items),
            "confusion_matrix": confusion_matrix(items),
            "disagreements": sum(item.human_score != item.judge_score for item in items),
            "requires_human_review": sum(item.requires_human_review for item in items),
        },
        "by_rubric": by_rubric,
        "by_judge_model": by_model,
        "high_variance_cases": high_variance,
        "disagreement_examples": disagreement_examples(items),
    }


def main() -> int:
    args = parse_args()
    try:
        human_rows = load_jsonl(args.human_labels, allow_empty=True)
        judge_rows = load_jsonl(args.judge_output)
        joined, missing = join_rows(
            human_rows,
            judge_rows,
            rubric_filter=set(args.rubric) if args.rubric else None,
            judge_model_filter=set(args.judge_model) if args.judge_model else None,
        )
        report = summarize(joined, missing_labels=missing, high_variance_threshold=args.high_variance_threshold)
        report["human_labels"] = str(args.human_labels)
        report["judge_output"] = str(args.judge_output)
    except Exception as exc:
        print(f"calibration report failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.fail_on_disagreement and report["overall"]["disagreements"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
