from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "capture_candidate_chatbot_responses.py"
DATASET = ROOT / "datasets" / "synthetic" / "recruiter-evidence-qa.jsonl"

spec = importlib.util.spec_from_file_location("capture_candidate_chatbot_responses", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError("could not load capture script")
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


class CaptureCandidateChatbotResponsesTests(unittest.TestCase):
    def test_select_rows_filters_ids_in_requested_order(self) -> None:
        rows = capture.validate_recruiter_dataset(DATASET)

        selected = capture.select_rows(
            rows,
            ids="private_sources_refusal,recruiter_container_orchestration",
            limit=None,
        )

        self.assertEqual([row.id for row in selected], ["private_sources_refusal", "recruiter_container_orchestration"])

    def test_capture_row_scores_valid_response(self) -> None:
        row = capture.validate_recruiter_dataset(DATASET)[0]
        original_post_chat = capture.post_chat

        def fake_post_chat(endpoint, payload, *, timeout_seconds):
            self.assertEqual(endpoint, "https://example.com/api/chat")
            self.assertEqual(payload["messages"][0]["content"], row.question)
            return 200, {
                "answer": row.referenceResponse,
                "citations": row.expected_sources,
                "evidenceStrength": row.expected_evidence_strength,
                "unsupportedClaims": [],
            }

        setattr(capture, "post_chat", fake_post_chat)
        try:
            result = capture.capture_row(
                row,
                endpoint="https://example.com/api/chat",
                session_prefix="unit-test",
                timeout_seconds=1,
            )
        finally:
            setattr(capture, "post_chat", original_post_chat)

        self.assertTrue(result["responseValid"])
        self.assertTrue(result["scorePassed"])
        self.assertEqual(result["httpStatus"], 200)

    def test_write_jsonl_and_summary_record_failures(self) -> None:
        rows = [
            {"id": "ok", "responseValid": True, "scorePassed": True},
            {"id": "bad", "responseValid": False, "scorePassed": False, "error": "response_contract_failed: citations"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "answers.jsonl"
            capture.write_jsonl(output, rows)
            loaded = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(loaded, rows)
        summary = capture.summarize(rows)
        self.assertEqual(summary["rows"], 2)
        self.assertEqual(summary["response_valid"], 1)
        self.assertEqual(summary["score_passed"], 1)
        self.assertEqual(summary["failures"][0]["id"], "bad")


if __name__ == "__main__":
    unittest.main()
