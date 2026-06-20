from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SCRIPT = SRC / "adapters" / "bedrock_model_eval.py"
DATASET = ROOT / "datasets" / "synthetic" / "recruiter-evidence-qa.jsonl"

spec = importlib.util.spec_from_file_location("bedrock_model_eval", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError("could not load Bedrock model eval adapter")
adapter = importlib.util.module_from_spec(spec)
sys.modules["bedrock_model_eval"] = adapter
spec.loader.exec_module(adapter)


class BedrockModelEvalAdapterTests(unittest.TestCase):
    def _captured_rows_for_dataset(self) -> list[dict[str, object]]:
        rows = adapter.validate_recruiter_dataset(DATASET)
        return [
            {
                "id": row.id,
                "answer": row.referenceResponse,
                "responseValid": True,
                "scorePassed": True,
            }
            for row in rows
        ]

    def test_conversion_writes_one_byoi_row_per_dataset_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            captured = tmp_path / "captured.jsonl"
            output = tmp_path / "bedrock-model-eval-byoi.jsonl"
            captured.write_text(
                "\n".join(json.dumps(row) for row in self._captured_rows_for_dataset()) + "\n",
                encoding="utf-8",
            )

            summary = adapter.convert_captured_answers_to_byoi(
                dataset_path=DATASET,
                input_path=captured,
                output_path=output,
                model_identifier="ryanprasad-ai-chatbot-v1-live-test",
            )
            byoi_rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(summary["byoi_rows"], len(byoi_rows))
        self.assertGreaterEqual(len(byoi_rows), 20)
        self.assertEqual({len(row["modelResponses"]) for row in byoi_rows}, {1})
        self.assertEqual(
            {row["modelResponses"][0]["modelIdentifier"] for row in byoi_rows},
            {"ryanprasad-ai-chatbot-v1-live-test"},
        )
        self.assertEqual(
            set(byoi_rows[0]),
            {"schema_version", "prompt", "referenceResponse", "category", "modelResponses"},
        )

    def test_reads_answer_from_raw_response_fallback(self) -> None:
        answer = adapter.captured_answer_from_row(
            {"id": "row-1", "rawResponse": {"answer": "fallback answer"}, "responseValid": True},
            line_no=7,
        )

        self.assertEqual(answer.row_id, "row-1")
        self.assertEqual(answer.response, "fallback answer")
        self.assertEqual(answer.source_line, 7)

    def test_rejects_duplicate_answer_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            captured = Path(tmp) / "captured.jsonl"
            captured.write_text(
                '\n'.join(
                    [
                        json.dumps({"id": "same", "answer": "first", "responseValid": True}),
                        json.dumps({"id": "same", "answer": "second", "responseValid": True}),
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate answer id same"):
                adapter.read_captured_answers(captured)

    def test_rejects_invalid_capture_rows_by_default(self) -> None:
        with self.assertRaisesRegex(ValueError, "responseValid=false"):
            adapter.captured_answer_from_row(
                {"id": "bad", "answer": "not useful", "responseValid": False},
                line_no=3,
            )

    def test_reports_missing_dataset_answers(self) -> None:
        rows = adapter.validate_recruiter_dataset(DATASET)
        answers = {rows[0].id: adapter.CapturedAnswer(rows[0].id, "only one answer", 1)}

        with self.assertRaisesRegex(ValueError, "missing answer rows"):
            adapter.build_byoi_rows(rows, answers, model_identifier="ryanprasad-ai-chatbot-v1")


if __name__ == "__main__":
    unittest.main()
