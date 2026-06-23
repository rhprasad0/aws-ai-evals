from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "human_label_workbench.py"

spec = importlib.util.spec_from_file_location("human_label_workbench", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError("could not load human_label_workbench script")
workbench = importlib.util.module_from_spec(spec)
sys.modules["human_label_workbench"] = workbench
spec.loader.exec_module(workbench)

WEB_SCRIPT = ROOT / "scripts" / "human_label_web_workbench.py"
web_spec = importlib.util.spec_from_file_location("human_label_web_workbench", WEB_SCRIPT)
if web_spec is None or web_spec.loader is None:
    raise RuntimeError("could not load human_label_web_workbench script")
web_workbench = importlib.util.module_from_spec(web_spec)
sys.modules["human_label_web_workbench"] = web_workbench
web_spec.loader.exec_module(web_workbench)


def example(example_id: str) -> dict[str, object]:
    return {
        "id": example_id,
        "question": "Where is the evidence?",
        "expected_sources": ["GitHub Profile README"],
        "must_include": ["evidence"],
        "must_not_claim": ["production ownership"],
        "expected_evidence_strength": "medium_high_public_project",
        "referenceResponse": "Synthetic reference response.",
        "category": "recruiter",
    }


def complete_slot(example_id: str = "row_one", rubric_id: str = "correctness", score: int = 2):
    return workbench.LabelSlot(
        example_id=example_id,
        rubric_id=rubric_id,
        score=score,
        expected_outcome="answered_from_public_evidence",
        expected_evidence_strength="medium_high_public_project",
        expected_failure_labels=[],
        human_rationale="Manual label rationale.",
    )


class HumanLabelWorkbenchTests(unittest.TestCase):
    def test_build_empty_label_state_creates_five_slots_per_example(self) -> None:
        slots = workbench.build_empty_slots([example("row_one"), example("row_two")])

        self.assertEqual(len(slots), 10)
        self.assertIn(("row_one", "correctness"), slots)
        self.assertIn(("row_two", "evidence_strength_calibration"), slots)
        self.assertIsNone(slots[("row_one", "correctness")].score)

    def test_row_from_slot_emits_human_label_contract(self) -> None:
        row = workbench.row_from_slot(complete_slot())

        self.assertEqual(row["schema_version"], "candidate-human-label/v1")
        self.assertEqual(row["example_id"], "row_one")
        self.assertEqual(row["rubric_id"], "correctness")
        self.assertEqual(row["rubric_version"], "candidate-correctness/v1")
        self.assertEqual(row["expected_score"], 2)
        self.assertEqual(row["expected_score_label"], "pass")
        self.assertEqual(row["labeler"], "human-curated-contract")

    def test_score_label_derivation(self) -> None:
        self.assertEqual(workbench.score_label(0), "fail")
        self.assertEqual(workbench.score_label(1), "partial")
        self.assertEqual(workbench.score_label(2), "pass")
        with self.assertRaises(ValueError):
            workbench.score_label(3)

    def test_explanation_dictionaries_cover_gui_values(self) -> None:
        workbench.assert_explanation_coverage()
        self.assertIn("Pass", workbench.SCORE_EXPLANATIONS[2])
        self.assertIn("public evidence", workbench.OUTCOME_EXPLANATIONS["answered_from_public_evidence"])
        self.assertIn("Lab", workbench.EVIDENCE_STRENGTH_EXPLANATIONS["medium_high_lab_project"])
        self.assertIn("Citation", workbench.FAILURE_LABEL_EXPLANATIONS["citation_invalid"])

    def test_bedrock_score_interpretation_keeps_non_exact_values_visible(self) -> None:
        self.assertEqual(workbench.bedrock_score_interpretation(0.0)["repo_score"], 0)
        self.assertEqual(workbench.bedrock_score_interpretation(0.5)["repo_score"], 1)
        self.assertEqual(workbench.bedrock_score_interpretation(1.0)["repo_score"], 2)

        low_mid = workbench.bedrock_score_interpretation(0.25)
        high_mid = workbench.bedrock_score_interpretation(0.75)
        self.assertFalse(low_mid["exact"])
        self.assertFalse(high_mid["exact"])
        self.assertIn("Between fail and partial", low_mid["note"])
        self.assertIn("Between partial and pass", high_mid["note"])

    def test_duplicate_loaded_labels_raise_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "labels.jsonl"
            row = workbench.row_from_slot(complete_slot())
            path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "duplicate labels"):
                workbench.load_label_slots(path)

    def test_clear_labels_archives_then_empties_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            labels = root / "human-labels.jsonl"
            archive_dir = root / "archive"
            labels.write_text(json.dumps(workbench.row_from_slot(complete_slot())) + "\n", encoding="utf-8")

            result = workbench.clear_labels(labels, archive_dir)

            self.assertEqual(result["archived_rows"], 1)
            self.assertEqual(labels.read_text(encoding="utf-8"), "")
            self.assertTrue(result["archive"].exists())
            self.assertIn("row_one", result["archive"].read_text(encoding="utf-8"))

    def test_validate_complete_labels_reports_empty_file_as_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset.jsonl"
            labels = root / "labels.jsonl"
            dataset.write_text(json.dumps(example("row_one")) + "\n", encoding="utf-8")
            labels.write_text("", encoding="utf-8")

            ok, issues = workbench.validate_complete_labels(dataset, labels)

            self.assertFalse(ok)
            self.assertIn("missing 5 label", "\n".join(issues))

    def test_draft_slots_round_trip_partial_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            draft = Path(tmp) / "draft-label-state.json"
            slots = workbench.build_empty_slots([example("row_one")])
            slot = slots[("row_one", "correctness")]
            slot.score = 1
            slot.expected_outcome = "needs_human_review"
            slot.expected_evidence_strength = "calibration_required"
            slot.expected_failure_labels = ["material_omission"]
            slot.human_rationale = "Half-labeled but not ready to export."

            workbench.save_draft(draft, slots)
            loaded = workbench.load_draft_slots(draft)

            restored = loaded[("row_one", "correctness")]
            self.assertEqual(restored.score, 1)
            self.assertEqual(restored.expected_outcome, "needs_human_review")
            self.assertEqual(restored.expected_failure_labels, ["material_omission"])
            self.assertEqual(restored.human_rationale, "Half-labeled but not ready to export.")

    def test_validate_complete_labels_accepts_full_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset.jsonl"
            labels = root / "labels.jsonl"
            examples = [example("row_one")]
            dataset.write_text(json.dumps(examples[0]) + "\n", encoding="utf-8")
            slots = workbench.build_empty_slots(examples)
            for key, slot in slots.items():
                slot.score = 2
                slot.expected_outcome = "answered_from_public_evidence"
                slot.expected_evidence_strength = "medium_high_public_project"
                slot.human_rationale = f"Manual rationale for {key[1]}."
            workbench.write_jsonl(labels, workbench.completed_rows(examples, slots))

            ok, issues = workbench.validate_complete_labels(dataset, labels)

            self.assertTrue(ok, issues)

    def test_dataset_rows_normalize_and_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dataset.jsonl"
            row = example("row_one")
            row["must_include"] = "evidence\nsource label\n"

            normalized = workbench.normalize_dataset_rows([row])
            workbench.write_dataset_jsonl(path, normalized)
            loaded = workbench.load_examples(path)

            self.assertEqual(loaded[0]["id"], "row_one")
            self.assertEqual(loaded[0]["must_include"], ["evidence", "source label"])
            self.assertEqual(list(loaded[0]), list(workbench.DATASET_ROW_KEYS))

    def test_dataset_duplicate_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate dataset id row_one"):
            workbench.normalize_dataset_rows([example("row_one"), example("row_one")])

    def test_invalid_dataset_save_does_not_overwrite_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dataset.jsonl"
            original = example("row_one")
            workbench.write_dataset_jsonl(path, workbench.normalize_dataset_rows([original]))
            before = path.read_text(encoding="utf-8")
            invalid = example("row_one")
            invalid["expected_evidence_strength"] = "unsupported"
            invalid["expected_sources"] = ["GitHub Profile README"]

            ok, issues, count = workbench.save_dataset_rows(path, [invalid])

            self.assertFalse(ok)
            self.assertEqual(count, 1)
            self.assertIn("expected_sources", "\n".join(issues))
            self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_source_label_options_are_loaded_from_schema(self) -> None:
        options = workbench.source_label_options()

        self.assertIn("GitHub Profile README", options)
        self.assertIn("content/profile.md", options)

    def test_web_payload_round_trips_slots(self) -> None:
        payload = {
            "slots": {
                "row_one::correctness": {
                    "example_id": "row_one",
                    "rubric_id": "correctness",
                    "score": 1,
                    "expected_outcome": "needs_human_review",
                    "expected_evidence_strength": "calibration_required",
                    "expected_failure_labels": ["material_omission"],
                    "human_rationale": "Needs review.",
                }
            }
        }

        slots = web_workbench.slots_from_payload(payload)

        slot = slots[("row_one", "correctness")]
        self.assertEqual(slot.score, 1)
        self.assertEqual(slot.expected_outcome, "needs_human_review")
        self.assertEqual(slot.expected_failure_labels, ["material_omission"])

    def test_web_dataset_payload_parses_newline_lists(self) -> None:
        row = example("row_one")
        row["must_include"] = "evidence\nsource label"
        payload = {"datasetRows": [row]}

        rows = web_workbench.dataset_rows_from_payload(payload)

        self.assertEqual(rows[0]["must_include"], ["evidence", "source label"])

    def test_web_dataset_payload_accepts_added_row(self) -> None:
        added = example("new_recruiter_row")
        added["expected_sources"] = []
        added["expected_evidence_strength"] = "calibration_required"
        payload = {"datasetRows": [example("row_one"), added]}

        rows = web_workbench.dataset_rows_from_payload(payload)

        self.assertEqual([row["id"] for row in rows], ["row_one", "new_recruiter_row"])
        self.assertEqual(list(rows[1]), list(workbench.DATASET_ROW_KEYS))

    def test_web_dataset_payload_rejects_duplicate_added_row_id(self) -> None:
        payload = {"datasetRows": [example("row_one"), example("row_one")]}

        with self.assertRaisesRegex(ValueError, "duplicate dataset id row_one"):
            web_workbench.dataset_rows_from_payload(payload)

    def test_web_app_serves_browser_markup(self) -> None:
        markup = web_workbench.app_html()

        self.assertIn("Week 5 Human Label Workbench", markup)
        self.assertIn("Dataset row editor", markup)
        self.assertIn("/dataset-editor", markup)
        self.assertIn("Open dataset row editor", markup)
        self.assertIn("Save dataset changes", markup)
        self.assertIn("Export completed labels", markup)
        self.assertIn("/state", markup)
        self.assertIn("split('\\n')", markup)
        self.assertIn("join('\\n')", markup)
        self.assertNotIn("split('\n')", markup)

    def test_dataset_editor_app_serves_add_delete_markup(self) -> None:
        markup = web_workbench.dataset_editor_html()

        self.assertIn("Dataset Row Editor", markup)
        self.assertIn("/state", markup)
        self.assertIn("/dataset", markup)
        self.assertIn("/dataset/validate", markup)
        self.assertIn("Add row", markup)
        self.assertIn("Delete row", markup)
        self.assertIn("Confirm delete row", markup)
        self.assertIn("deleteSelectedRow", markup)
        self.assertIn("This deletes only the browser copy until you save", markup)
        self.assertIn("Cannot delete the final row", markup)
        self.assertIn("Save dataset changes", markup)
        self.assertIn("Reload dataset from disk", markup)
        self.assertIn("Evidence strength", markup)
        self.assertIn("Plain-English helper text", markup)

    def test_web_state_loads_draft_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset.jsonl"
            labels = root / "labels.jsonl"
            draft = root / "draft.json"
            dataset.write_text(json.dumps(example("row_one")) + "\n", encoding="utf-8")
            labels.write_text("", encoding="utf-8")
            slots = workbench.build_empty_slots([example("row_one")])
            slots[("row_one", "correctness")].score = 1
            slots[("row_one", "correctness")].human_rationale = "Saved draft."
            workbench.save_draft(draft, slots)

            args = type("Args", (), {"dataset": dataset, "labels": labels, "draft": draft, "byoi_jsonl": None, "captured_jsonl": None})()
            payload = web_workbench.state_payload(args)

            self.assertEqual(payload["slots"]["row_one::correctness"]["score"], 1)
            self.assertEqual(payload["slots"]["row_one::correctness"]["human_rationale"], "Saved draft.")
            self.assertEqual(payload["datasetRows"][0]["id"], "row_one")
            self.assertIn("GitHub Profile README", payload["sourceLabelOptions"])


if __name__ == "__main__":
    unittest.main()
