from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_chat_app_events.py"
SCHEMA = ROOT / "schemas" / "aws-evals" / "normalized-app-event.schema.json"

spec = importlib.util.spec_from_file_location("export_chat_app_events", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError("could not load export script")
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


BEDROCK_MESSAGE = (
    "2026-06-18T12:46:57 [INFO]\trequest-id\tchat_app_event "
    + json.dumps(
        {
            "citation_count": 2,
            "citation_labels": ["aws-devops-lab README", "airgap-aiops README"],
            "elapsed_ms": 1144,
            "event": "chat_response_completed",
            "evidence_strength": "medium_high_lab_project",
            "input_tokens": 1480,
            "max_tokens": 768,
            "model_id": "us.amazon.nova-2-lite-v1:0",
            "output_tokens": 226,
            "prompt_template_version": "candidate-evidence-v1",
            "request_class": "chat",
            "response_source": "bedrock",
            "total_tokens": 1706,
            "unsupported_claim_count": 0,
        },
        sort_keys=True,
    )
)

GUARDRAIL_MESSAGE = (
    "2026-06-18T12:46:58 [INFO]\trequest-id\tchat_app_event "
    + json.dumps(
        {
            "citation_count": 0,
            "citation_labels": [],
            "event": "chat_response_completed",
            "evidence_strength": "unsupported_private",
            "max_tokens": 768,
            "model_id": "us.amazon.nova-2-lite-v1:0",
            "prompt_template_version": "candidate-evidence-v1",
            "request_class": "chat",
            "response_source": "guardrail",
            "unsupported_claim_count": 1,
        },
        sort_keys=True,
    )
)


class ExportChatAppEventsTests(unittest.TestCase):
    def test_extract_event_payload_adds_schema_version(self) -> None:
        event = exporter.extract_event_payload(BEDROCK_MESSAGE)

        self.assertIsNotNone(event)
        self.assertEqual(event["schema_version"], "normalized-app-event/v1")
        self.assertEqual(event["response_source"], "bedrock")
        self.assertEqual(event["total_tokens"], 1706)
        self.assertNotIn("answer", event)

    def test_iter_normalized_events_ignores_non_app_messages(self) -> None:
        payload = {
            "events": [
                {"message": "START RequestId: fake"},
                {"message": BEDROCK_MESSAGE},
                {"message": GUARDRAIL_MESSAGE},
            ]
        }

        events = list(exporter.iter_normalized_events(payload))

        self.assertEqual(len(events), 2)
        self.assertEqual([event["response_source"] for event in events], ["bedrock", "guardrail"])

    def test_validate_events_rejects_leaky_extra_fields(self) -> None:
        schema = exporter.load_schema(SCHEMA)
        event = exporter.extract_event_payload(BEDROCK_MESSAGE)
        assert event is not None
        event["answer"] = "raw answer should never be exported"

        with self.assertRaises(exporter.ExportError) as raised:
            exporter.validate_events([event], schema)

        self.assertIn("Additional properties", str(raised.exception))

    def test_write_jsonl_round_trips_normalized_events(self) -> None:
        events = list(exporter.iter_normalized_events({"events": [{"message": BEDROCK_MESSAGE}]}))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "app-events.jsonl"
            exporter.write_jsonl(output, events)
            loaded = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(loaded, events)


if __name__ == "__main__":
    unittest.main()
