from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import eval_harness


ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


class EvalHarnessTests(unittest.TestCase):
    def test_default_reviewed_fixture_summary_is_mechanical(self) -> None:
        result = eval_harness.run_harness(
            ROOT,
            ROOT / eval_harness.DEFAULT_EXAMPLES,
            ROOT / eval_harness.DEFAULT_RESPONSES,
            ROOT / eval_harness.DEFAULT_LABELS,
        )

        self.assertEqual([], result.failures)
        self.assertEqual(18, result.summary["totalExamples"])
        self.assertEqual(3, result.summary["capturedResponses"])
        self.assertEqual(3, result.summary["humanLabels"])
        self.assertEqual(3, result.summary["labeledResponses"])
        self.assertEqual({"pass": 3, "fail": 0}, result.summary["outcomes"])
        self.assertEqual(15, result.summary["missingResponses"]["count"])
        self.assertEqual(15, result.summary["missingLabels"]["count"])
        self.assertEqual(0, result.summary["orphanResponses"]["count"])
        self.assertEqual(0, result.summary["orphanLabels"]["count"])
        self.assertGreaterEqual(result.summary["productionAiProbes"]["total"], 1)
        self.assertEqual(1, result.summary["productionAiProbes"]["pass"])

    def test_reports_missing_response_and_label(self) -> None:
        all_examples = {row["exampleId"]: row for row in load_jsonl(ROOT / "datasets/synthetic/recruiter-evidence-qa.jsonl")}
        responses = load_jsonl(ROOT / eval_harness.DEFAULT_RESPONSES)[:1]
        labels = load_jsonl(ROOT / eval_harness.DEFAULT_LABELS)[:1]
        examples = [all_examples[responses[0]["exampleId"]], next(row for row in all_examples.values() if row["exampleId"] != responses[0]["exampleId"])]
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            examples_path = base / "examples.jsonl"
            responses_path = base / "responses.jsonl"
            labels_path = base / "labels.jsonl"
            write_jsonl(examples_path, examples)
            write_jsonl(responses_path, responses)
            write_jsonl(labels_path, labels)

            result = eval_harness.run_harness(ROOT, examples_path, responses_path, labels_path)

        self.assertEqual([], result.failures)
        self.assertEqual(1, result.summary["missingResponses"]["count"])
        self.assertEqual(1, result.summary["missingLabels"]["count"])
        self.assertEqual([examples[1]["exampleId"]], result.summary["missingResponses"]["exampleIds"])
        self.assertEqual([examples[1]["exampleId"]], result.summary["missingLabels"]["exampleIds"])

    def test_label_run_id_must_match_response_run_id(self) -> None:
        responses = load_jsonl(ROOT / eval_harness.DEFAULT_RESPONSES)[:1]
        labels = load_jsonl(ROOT / eval_harness.DEFAULT_LABELS)[:1]
        all_examples = {row["exampleId"]: row for row in load_jsonl(ROOT / "datasets/synthetic/recruiter-evidence-qa.jsonl")}
        examples = [all_examples[responses[0]["exampleId"]]]
        labels[0] = {**labels[0], "runId": "different-run-id"}
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            examples_path = base / "examples.jsonl"
            responses_path = base / "responses.jsonl"
            labels_path = base / "labels.jsonl"
            write_jsonl(examples_path, examples)
            write_jsonl(responses_path, responses)
            write_jsonl(labels_path, labels)

            result = eval_harness.run_harness(ROOT, examples_path, responses_path, labels_path)

        self.assertTrue(any("does not match response runId" in failure.message for failure in result.failures))

    def test_cli_json_summary(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/eval_harness.py", "--json"],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )

        summary = json.loads(completed.stdout)
        self.assertEqual(3, summary["humanLabels"])
        self.assertEqual(3, summary["labeledResponses"])

    def test_markdown_summary_keeps_quality_caveat_and_tables(self) -> None:
        result = eval_harness.run_harness(
            ROOT,
            ROOT / eval_harness.DEFAULT_EXAMPLES,
            ROOT / eval_harness.DEFAULT_RESPONSES,
            ROOT / eval_harness.DEFAULT_LABELS,
        )

        markdown = eval_harness.render_markdown(result.summary)

        self.assertIn("# Local Eval Harness Summary", markdown)
        self.assertIn("Mechanical summary only", markdown)
        self.assertIn("| Dataset examples | 18 |", markdown)
        self.assertIn("| Pass | 3 |", markdown)
        self.assertIn("| Human fail | 0 |", markdown)
        self.assertIn("## Missing Review Work", markdown)
        self.assertNotIn("model passed", markdown.lower())

    def test_cli_markdown_summary(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/eval_harness.py", "--markdown"],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )

        self.assertIn("# Local Eval Harness Summary", completed.stdout)
        self.assertIn("| Human labels | 3 |", completed.stdout)


if __name__ == "__main__":
    unittest.main()
