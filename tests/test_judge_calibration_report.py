from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "judge_calibration_report.py"
HUMAN_LABELS = ROOT / "datasets" / "synthetic" / "human-labels.jsonl"

spec = importlib.util.spec_from_file_location("judge_calibration_report", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError("could not load calibration report script")
reporter = importlib.util.module_from_spec(spec)
sys.modules["judge_calibration_report"] = reporter
spec.loader.exec_module(reporter)


def human_label(example_id: str = "recruiter_container_orchestration", rubric_id: str = "correctness", score: int = 2):
    label = "pass" if score == 2 else "partial" if score == 1 else "fail"
    return {
        "schema_version": "candidate-human-label/v1",
        "example_id": example_id,
        "source_dataset": "datasets/synthetic/recruiter-evidence-qa.jsonl",
        "rubric_id": rubric_id,
        "rubric_version": "candidate-correctness/v1",
        "expected_score": score,
        "expected_score_label": label,
        "expected_failure_labels": [],
        "expected_evidence_strength": "medium_high_lab_project",
        "expected_outcome": "answered_from_public_evidence",
        "human_rationale": "Synthetic test label.",
        "labeler": "human-curated-contract",
        "label_version": "v1",
    }


def judge_output(
    example_id: str = "recruiter_container_orchestration",
    rubric_id: str = "correctness",
    score: int = 2,
    repetition_index: int = 1,
    run_id: str = "test-run",
):
    label = "pass" if score == 2 else "partial" if score == 1 else "fail"
    return {
        "schema_version": "candidate-judge-output/v1",
        "example_id": example_id,
        "run_id": run_id,
        "rubric_id": rubric_id,
        "rubric_version": "candidate-correctness/v1",
        "judge_model_id": "us.anthropic.claude-sonnet-4-6",
        "repetition_index": repetition_index,
        "score": score,
        "score_label": label,
        "rationale": "Synthetic test judgment.",
        "failure_labels": [],
        "requires_human_review": score != 2,
    }


class JudgeCalibrationReportTests(unittest.TestCase):
    def test_join_and_summarize_perfect_agreement(self) -> None:
        joined, missing = reporter.join_rows(
            [human_label(score=2), human_label("unsupported_large_k8s_prod", "refusal_appropriateness", 2)],
            [judge_output(score=2), judge_output("unsupported_large_k8s_prod", "refusal_appropriateness", 2)],
        )

        summary = reporter.summarize(joined, missing_labels=missing, high_variance_threshold=1)

        self.assertEqual(summary["rows_joined"], 2)
        self.assertEqual(summary["overall"]["agreement"], 1.0)
        self.assertEqual(summary["overall"]["disagreements"], 0)
        self.assertEqual(summary["missing_human_labels"], [])

    def test_summarize_reports_disagreement_and_confusion_matrix(self) -> None:
        joined, missing = reporter.join_rows([human_label(score=2)], [judge_output(score=0)])

        summary = reporter.summarize(joined, missing_labels=missing, high_variance_threshold=1)

        self.assertEqual(summary["overall"]["agreement"], 0.0)
        self.assertEqual(summary["overall"]["confusion_matrix"]["2"]["0"], 1)
        self.assertEqual(summary["disagreement_examples"][0]["judge_score"], 0)

    def test_repeated_run_variance_flags_score_range(self) -> None:
        joined, missing = reporter.join_rows(
            [human_label(score=2)],
            [judge_output(score=2, repetition_index=1), judge_output(score=1, repetition_index=2)],
        )

        summary = reporter.summarize(joined, missing_labels=missing, high_variance_threshold=1)

        self.assertEqual(len(summary["high_variance_cases"]), 1)
        self.assertEqual(summary["high_variance_cases"][0]["scores"], [2, 1])
        self.assertEqual(summary["high_variance_cases"][0]["score_range"], 1)

    def test_missing_human_label_is_reported(self) -> None:
        joined, missing = reporter.join_rows([], [judge_output()])

        self.assertEqual(joined, [])
        self.assertEqual(missing[0]["example_id"], "recruiter_container_orchestration")

    def test_empty_human_label_file_reports_missing_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            human_path = Path(tmp) / "human.jsonl"
            judge_path = Path(tmp) / "judge.jsonl"
            human_path.write_text("", encoding="utf-8")
            judge_path.write_text(json.dumps(judge_output(score=2)) + "\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--human-labels",
                    str(human_path),
                    "--judge-output",
                    str(judge_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"rows_joined": 0', result.stdout)
        self.assertIn('"missing_human_labels"', result.stdout)
        self.assertIn('"agreement": null', result.stdout)

    def test_fail_on_disagreement_ignores_missing_human_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            human_path = Path(tmp) / "human.jsonl"
            judge_path = Path(tmp) / "judge.jsonl"
            human_path.write_text("", encoding="utf-8")
            judge_path.write_text(json.dumps(judge_output(score=0)) + "\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--human-labels",
                    str(human_path),
                    "--judge-output",
                    str(judge_path),
                    "--fail-on-disagreement",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"disagreements": 0', result.stdout)

    def test_cli_outputs_report_and_fail_on_disagreement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            human_path = Path(tmp) / "human.jsonl"
            judge_path = Path(tmp) / "judge.jsonl"
            human_path.write_text(json.dumps(human_label(score=2)) + "\n", encoding="utf-8")
            judge_path.write_text(json.dumps(judge_output(score=0)) + "\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--human-labels",
                    str(human_path),
                    "--judge-output",
                    str(judge_path),
                    "--fail-on-disagreement",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn('"disagreements": 1', result.stdout)

    def test_real_fixture_report_runs(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--human-labels",
                str(ROOT / "tests" / "fixtures" / "datasets" / "valid" / "human-label-valid.jsonl"),
                "--judge-output",
                str(ROOT / "tests" / "fixtures" / "datasets" / "valid" / "judge-output-valid.jsonl"),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"rows_joined": 1', result.stdout)
        self.assertIn('"missing_human_labels"', result.stdout)


if __name__ == "__main__":
    unittest.main()
