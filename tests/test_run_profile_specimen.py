from __future__ import annotations

import json
import subprocess
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from jsonschema import Draft202012Validator, FormatChecker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import run_profile_specimen


ROOT = Path(__file__).resolve().parents[1]


class RunProfileSpecimenTests(unittest.TestCase):
    class FakeBedrockClient:
        def __init__(self) -> None:
            self.calls = []

        def converse(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "output": {
                    "message": {
                        "content": [
                            {
                                "text": json.dumps(
                                    {
                                        "answer": "profile.md does not support that production AI claim.",
                                        "responseKind": "not_supported",
                                    }
                                )
                            }
                        ]
                    }
                }
            }

    def test_select_examples_supports_limit_example_id_and_production_probe_filters(self) -> None:
        rows = [
            {"exampleId": "a", "productionAiProbe": True},
            {"exampleId": "b", "productionAiProbe": False},
            {"exampleId": "c", "productionAiProbe": True},
        ]

        self.assertEqual(["a"], [row["exampleId"] for row in run_profile_specimen.select_examples(rows, limit=1)])
        self.assertEqual(["c"], [row["exampleId"] for row in run_profile_specimen.select_examples(rows, example_ids=["c"])])
        self.assertEqual(
            ["a", "c"],
            [row["exampleId"] for row in run_profile_specimen.select_examples(rows, production_probes=True)],
        )
        with self.assertRaisesRegex(ValueError, "exampleId not found"):
            run_profile_specimen.select_examples(rows, example_ids=["missing"])

    def test_stub_capture_writes_schema_valid_jsonl(self) -> None:
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "captured.jsonl"
            records = run_profile_specimen.run_stub_capture(
                root=ROOT,
                dataset_path=ROOT / "datasets/synthetic/recruiter-evidence-qa.jsonl",
                profile_path=ROOT / "profile.md",
                output_path=output,
                run_id="local-stub-test",
                example_ids=["prod-ai-direct-001", "off-topic-canary-001"],
                captured_at=datetime(2026, 6, 28, 17, 0, tzinfo=UTC),
            )

            lines = output.read_text(encoding="utf-8").splitlines()
            schema = json.loads((ROOT / "schemas/captured-response.schema.json").read_text(encoding="utf-8"))
            validator = Draft202012Validator(schema, format_checker=FormatChecker())
            parsed = [json.loads(line) for line in lines]
            errors = [error for record in parsed for error in validator.iter_errors(record)]

            self.assertEqual(2, len(records))
            self.assertEqual(2, len(lines))
            self.assertEqual([], errors)
            self.assertEqual("not_supported", parsed[0]["response"]["responseKind"])
            self.assertEqual("refusal", parsed[1]["response"]["responseKind"])
            self.assertNotIn("raw_response", json.dumps(parsed))

    def test_bedrock_mode_normalizes_response_without_storing_provider_envelope(self) -> None:
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "captured.jsonl"
            client = self.FakeBedrockClient()
            records = run_profile_specimen.run_capture(
                root=ROOT,
                dataset_path=ROOT / "datasets/synthetic/recruiter-evidence-qa.jsonl",
                profile_path=ROOT / "profile.md",
                output_path=output,
                run_id="local-bedrock-test",
                mode="bedrock",
                model_id="us.amazon.nova-2-lite-v1:0",
                example_ids=["prod-ai-direct-001"],
                captured_at=datetime(2026, 6, 28, 17, 0, tzinfo=UTC),
                bedrock_client=client,
            )

            payload = output.read_text(encoding="utf-8")

            self.assertEqual(1, len(records))
            self.assertEqual("us.amazon.nova-2-lite-v1:0", records[0]["modelId"])
            self.assertEqual("not_supported", records[0]["response"]["responseKind"])
            self.assertEqual(1, len(client.calls))
            self.assertIn("messages", client.calls[0])
            self.assertNotIn("output", payload)
            self.assertNotIn("message", records[0])

    def test_bedrock_blind_prompt_mode_hides_behavior_metadata(self) -> None:
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "captured.jsonl"
            client = self.FakeBedrockClient()
            records = run_profile_specimen.run_capture(
                root=ROOT,
                dataset_path=ROOT / "datasets/synthetic/recruiter-evidence-qa.jsonl",
                profile_path=ROOT / "profile.md",
                output_path=output,
                run_id="local-bedrock-blind-test",
                mode="bedrock",
                prompt_mode="blind",
                model_id="us.amazon.nova-2-lite-v1:0",
                example_ids=["prod-ai-direct-001"],
                captured_at=datetime(2026, 6, 28, 17, 0, tzinfo=UTC),
                bedrock_client=client,
            )
            prompt_text = client.calls[0]["messages"][0]["content"][0]["text"]

            self.assertEqual("profile-only-v1-blind", records[0]["promptVersion"])
            self.assertNotIn("expectedBehavior", prompt_text)
            self.assertNotIn("requestClass", prompt_text)
            self.assertNotIn("productionAiProbe", prompt_text)
            self.assertNotIn("say_not_supported", prompt_text)

    def test_extract_converse_text_requires_text_blocks(self) -> None:
        with self.assertRaisesRegex(ValueError, "text content"):
            run_profile_specimen.extract_converse_text({"output": {"message": {"content": []}}})

    def test_cli_writes_limited_production_probe_output(self) -> None:
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "prod-probes.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_profile_specimen.py",
                    "--production-probes",
                    "--limit",
                    "2",
                    "--run-id",
                    "local-stub-cli",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

            self.assertIn("OK: wrote 2 captured response", result.stdout)
            self.assertEqual(2, len(rows))
            self.assertTrue(all(row["runId"] == "local-stub-cli" for row in rows))
            self.assertTrue(all(row["response"]["responseKind"] in {"caveat", "not_supported"} for row in rows))


if __name__ == "__main__":
    unittest.main()
