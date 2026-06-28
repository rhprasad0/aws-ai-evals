from __future__ import annotations

import json
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import dataset_workbench as workbench


SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schemaVersion",
        "exampleId",
        "question",
        "requestClass",
        "expectedBehavior",
        "sourceSupport",
        "expectedAnswerNotes",
        "productionAiProbe",
    ],
    "properties": {
        "schemaVersion": {"const": "eval-example/v1"},
        "exampleId": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]{2,79}$"},
        "question": {"type": "string", "minLength": 8},
        "requestClass": {
            "oneOf": [
                {"const": "answerable_public_evidence", "description": "The question should be answerable from profile.md."},
                {"const": "unsupported_or_overclaim", "description": "The question asks for an unsupported claim."},
                {"const": "off_topic_or_abuse", "description": "The prompt is outside recruiter-evidence Q&A."},
            ]
        },
        "expectedBehavior": {
            "oneOf": [
                {"const": "answer_with_public_evidence", "description": "Answer directly using profile.md evidence."},
                {"const": "answer_with_caveat", "description": "Answer with an explicit caveat."},
                {"const": "say_not_supported", "description": "Say profile.md does not support the claim."},
                {"const": "refuse_or_redirect", "description": "Refuse or redirect off-contract prompts."},
            ]
        },
        "sourceSupport": {
            "oneOf": [
                {"const": "supported", "description": "profile.md should support a direct answer."},
                {"const": "partially_supported", "description": "profile.md supports adjacent evidence."},
                {"const": "unsupported", "description": "profile.md does not support the claim."},
                {"const": "not_applicable", "description": "Source support is not the main issue."},
            ]
        },
        "expectedAnswerNotes": {"type": "string", "minLength": 8},
        "mustAvoid": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
        "productionAiProbe": {"type": "boolean"},
    },
}


def row(example_id: str = "prod-ai-001") -> dict:
    return {
        "schemaVersion": "eval-example/v1",
        "exampleId": example_id,
        "question": "Does this profile support production AI experience?",
        "requestClass": "unsupported_or_overclaim",
        "expectedBehavior": "answer_with_caveat",
        "sourceSupport": "partially_supported",
        "expectedAnswerNotes": "Say the profile does not support direct production AI ownership, then pivot to adjacent evidence.",
        "mustAvoid": ["claiming production AI ownership"],
        "productionAiProbe": True,
    }


class DatasetWorkbenchTests(unittest.TestCase):
    def write_schema(self, root: Path) -> Path:
        schema_path = root / "schema.json"
        schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
        return schema_path

    def write_dataset(self, root: Path, rows: list[dict]) -> Path:
        path = root / "dataset.jsonl"
        path.write_text(workbench.dump_jsonl(rows), encoding="utf-8")
        return path

    def test_jsonl_round_trip_preserves_line_count_and_order(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [row("prod-ai-001"), row("prod-ai-002")]
            path = self.write_dataset(root, rows)

            loaded = workbench.load_jsonl(path)
            dumped = workbench.dump_jsonl(loaded)

            self.assertEqual(len(loaded), 2)
            self.assertEqual(dumped.count("\n"), 2)
            self.assertTrue(dumped.startswith('{"schemaVersion":"eval-example/v1","exampleId":"prod-ai-001"'))

    def test_malformed_json_reports_line_number(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text('{"ok": true}\n{bad}\n', encoding="utf-8")

            with self.assertRaisesRegex(workbench.DatasetParseError, "Line 2"):
                workbench.load_jsonl(path)

    def test_validation_reports_duplicate_ids_and_schema_errors(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_path = self.write_schema(root)
            first = row("prod-ai-001")
            second = row("prod-ai-001")
            second["unexpected"] = "nope"

            issues = workbench.validate_records([first, second], schema_path)
            messages = "\n".join(issue.message for issue in issues)
            fields = {issue.field for issue in issues}

            self.assertIn("Duplicate exampleId", messages)
            self.assertIn("additionalProperties", fields)

    def test_state_update_save_and_stale_file_protection(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_path = self.write_schema(root)
            dataset_path = self.write_dataset(root, [row("prod-ai-001")])
            state = workbench.WorkbenchState(dataset_path, schema_path)

            updated = row("prod-ai-001")
            updated["question"] = "What production AI ownership evidence is supported?"
            self.assertTrue(state.update_record("prod-ai-001", updated))
            self.assertTrue(state.dirty)
            state.save()
            self.assertFalse(state.dirty)
            self.assertIn("ownership evidence", dataset_path.read_text(encoding="utf-8"))

            state.update_record("prod-ai-001", updated)
            time.sleep(0.01)
            dataset_path.write_text(workbench.dump_jsonl([row("prod-ai-001")]), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "changed on disk"):
                state.save()

    def test_state_rejects_missing_record_and_readonly_id_change(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_path = self.write_schema(root)
            dataset_path = self.write_dataset(root, [row("prod-ai-001")])
            state = workbench.WorkbenchState(dataset_path, schema_path)

            self.assertFalse(state.update_record("missing-id", row("missing-id")))
            with self.assertRaisesRegex(ValueError, "read-only"):
                state.update_record("prod-ai-001", row("prod-ai-002"))

    def test_html_contains_enum_helper_copy_and_profile_context(self) -> None:
        markup = workbench.app_html()

        self.assertIn("No model calls", markup)
        self.assertIn("mystery-meat enums", markup)
        self.assertIn("Profile context", markup)
        self.assertIn("read-only", markup)
        self.assertIn("productionAiProbe", markup)

    def test_profile_payload_is_read_only_context(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_path = self.write_schema(root)
            dataset_path = self.write_dataset(root, [row("prod-ai-001")])
            profile_path = root / "profile.md"
            profile_path.write_text("# Profile\n\nOnly source context.\n", encoding="utf-8")
            state = workbench.WorkbenchState(dataset_path, schema_path, profile_path)

            payload = state.payload()

            self.assertTrue(payload["profileAvailable"])
            self.assertEqual(state.profile_text(), "# Profile\n\nOnly source context.\n")

    def test_http_api_returns_records_and_rejects_invalid_update(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_path = self.write_schema(root)
            dataset_path = self.write_dataset(root, [row("prod-ai-001")])
            state = workbench.WorkbenchState(dataset_path, schema_path)
            server = workbench.make_server(state, "127.0.0.1", 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                with urllib.request.urlopen(base + "/api/records") as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(len(payload["records"]), 1)
                self.assertIn("requestClass", payload["options"])

                invalid = row("prod-ai-001")
                invalid.pop("question")
                request = urllib.request.Request(
                    base + "/api/records/prod-ai-001",
                    data=json.dumps(invalid).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertGreater(len(payload["issues"]), 0)

                save_request = urllib.request.Request(base + "/api/save", data=b"", method="POST")
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(save_request)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
