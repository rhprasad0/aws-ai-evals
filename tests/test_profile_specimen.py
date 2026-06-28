from __future__ import annotations

import json
import subprocess
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import profile_specimen


ROOT = Path(__file__).resolve().parents[1]


class ProfileSpecimenTests(unittest.TestCase):
    def test_prompt_uses_profile_delimiters_and_minimal_response_contract(self) -> None:
        specimen_input = profile_specimen.SpecimenInput(
            example_id="prod-ai-direct-001",
            question="Does Ryan have production AI experience?",
            request_class="unsupported_or_overclaim",
            expected_behavior="say_not_supported",
            production_ai_probe=True,
        )

        prompt = profile_specimen.build_prompt(specimen_input, "# Profile\n\nOnly source content.")

        self.assertIn(profile_specimen.PROFILE_START, prompt)
        self.assertIn(profile_specimen.PROFILE_END, prompt)
        self.assertIn("using only the delimited profile.md", prompt)
        self.assertIn("Do not use private notes", prompt)
        self.assertIn('"answer"', prompt)
        self.assertIn('"responseKind"', prompt)
        self.assertIn("Do not include citations", prompt)
        self.assertIn("productionAiProbe: true", prompt)

    def test_normalize_model_response_accepts_fenced_json_and_rejects_extra_kind(self) -> None:
        response = profile_specimen.normalize_model_response(
            '```json\n{"answer":"No, profile.md does not support that claim.","responseKind":"not_supported"}\n```'
        )

        self.assertEqual(
            {
                "answer": "No, profile.md does not support that claim.",
                "responseKind": "not_supported",
            },
            response,
        )
        with self.assertRaisesRegex(ValueError, "responseKind"):
            profile_specimen.normalize_model_response('{"answer":"hi","responseKind":"score"}')

    def test_captured_response_record_matches_schema(self) -> None:
        specimen_input = profile_specimen.SpecimenInput(
            example_id="prod-ai-direct-001",
            question="Does Ryan have production AI experience?",
        )
        profile_text = "# Profile\n\nOnly source content."
        record = profile_specimen.captured_response_record(
            specimen_input,
            {"answer": "Not supported by profile.md.", "responseKind": "not_supported"},
            run_id="local-stub-001",
            model_id="stub-local",
            profile_text=profile_text,
            captured_at=datetime(2026, 6, 28, 16, 0, tzinfo=UTC),
        )
        schema = json.loads((ROOT / "schemas/captured-response.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())

        errors = list(validator.iter_errors(record))

        self.assertEqual([], errors)
        self.assertEqual("captured-response/v1", record["schemaVersion"])
        self.assertEqual("profile-only-v1", record["promptVersion"])
        self.assertTrue(record["profileVersion"].startswith("profile-md-"))

    def test_cli_prompt_and_stub_modes_run(self) -> None:
        prompt = subprocess.run(
            [sys.executable, "scripts/profile_specimen.py", "--example-id", "prod-ai-direct-001", "--prompt"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertIn("## Task", prompt.stdout)
        self.assertIn("Does Ryan have production AI experience?", prompt.stdout)

        stub = subprocess.run(
            [sys.executable, "scripts/profile_specimen.py", "--example-id", "off-topic-canary-001"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        record = json.loads(stub.stdout)
        self.assertEqual("captured-response/v1", record["schemaVersion"])
        self.assertEqual("refusal", record["response"]["responseKind"])


if __name__ == "__main__":
    unittest.main()
