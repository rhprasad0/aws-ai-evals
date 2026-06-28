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
