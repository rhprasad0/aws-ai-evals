from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import label_workbench

ROOT = Path(__file__).resolve().parents[1]

def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")

class LabelWorkbenchTests(unittest.TestCase):
    def make_files(self, tmp: Path, count: int = 2) -> tuple[Path, Path, Path, Path]:
        responses = load_jsonl(ROOT / "tests/fixtures/captured-responses/live-smoke-reviewed.jsonl")[:count]
        examples_by_id = {row["exampleId"]: row for row in load_jsonl(ROOT / "datasets/synthetic/recruiter-evidence-qa.jsonl")}
        examples = [examples_by_id[row["exampleId"]] for row in responses]
        examples_path = tmp / "examples.jsonl"
        responses_path = tmp / "responses.jsonl"
        write_jsonl(examples_path, examples)
        write_jsonl(responses_path, responses)
        return examples_path, responses_path, tmp / "draft.json", tmp / "labels.jsonl"

    def make_state(self, tmp: Path, count: int = 2) -> label_workbench.LabelWorkbenchState:
        examples_path, responses_path, draft_path, output_path = self.make_files(tmp, count=count)
        return label_workbench.LabelWorkbenchState(
            examples_path,
            responses_path,
            draft_path,
            output_path,
            ROOT / "schemas/eval-example.schema.json",
            ROOT / "schemas/captured-response.schema.json",
            ROOT / "schemas/human-label.schema.json",
            ROOT / "profile.md",
        )

    def test_check_mode_loads_all_generated_response_rows(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            examples_path, responses_path, draft_path, output_path = self.make_files(tmp, count=3)
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/label_workbench.py",
                    "--check",
                    "--examples",
                    str(examples_path),
                    "--responses",
                    str(responses_path),
                    "--draft",
                    str(draft_path),
                    "--output",
                    str(output_path),
                ],
                cwd=ROOT,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            )

        self.assertIn("OK: 3 response row(s)", completed.stdout)
        self.assertIn("3 unlabeled", completed.stdout)

    def test_state_includes_rows_options_and_profile(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            state = self.make_state(Path(tmp_dir), count=1)
            api_state = state.api_state()

        self.assertEqual(1, api_state["summary"]["rows"])
        self.assertEqual(1, api_state["summary"]["unlabeled"])
        self.assertEqual("pass", api_state["options"]["humanOutcome"][0]["value"])
        self.assertIn("production_ai_overclaim", [item["value"] for item in api_state["options"]["failureTags"]])
        self.assertIsInstance(api_state["profileText"], str)

    def test_draft_save_and_reload_preserves_partial_progress(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            state = self.make_state(tmp, count=1)
            example_id = state.rows()[0]["example"]["exampleId"]
            state.save_draft({example_id: {"humanOutcome": "pass", "reviewNotes": "Looks good."}})
            reloaded = self.make_state(tmp, count=1)

        label = reloaded.rows()[0]["label"]
        self.assertEqual("pass", label["humanOutcome"])
        self.assertEqual("Looks good.", label["reviewNotes"])

    def test_export_rejects_incomplete_labels(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            state = self.make_state(Path(tmp_dir), count=2)
            first_id = state.rows()[0]["example"]["exampleId"]
            issues = state.export_labels({first_id: {"humanOutcome": "pass"}})

        self.assertTrue(any(issue.field == "humanOutcome" for issue in issues))

    def test_export_writes_schema_valid_complete_labels(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            state = self.make_state(Path(tmp_dir), count=2)
            labels = {row["example"]["exampleId"]: {"humanOutcome": "pass", "reviewNotes": "Accepted."} for row in state.rows()}
            issues = state.export_labels(labels)
            exported = load_jsonl(state.output_path)

        self.assertEqual([], issues)
        self.assertEqual(2, len(exported))
        self.assertTrue(all(row["humanOutcome"] == "pass" for row in exported))
        self.assertTrue(all(row["runId"] == "local-bedrock-smoke3-reviewed" for row in exported))

if __name__ == "__main__":
    unittest.main()
