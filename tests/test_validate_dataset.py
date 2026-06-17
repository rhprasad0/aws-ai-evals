from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_dataset.py"
SCHEMA = ROOT / "schemas" / "recruiter-evidence-qa.schema.json"
RUN_MANIFEST_SCHEMA = ROOT / "schemas" / "run-manifest.schema.json"
FIXTURES = ROOT / "tests" / "fixtures" / "datasets"


class ValidateDatasetFixtureTests(unittest.TestCase):
    def run_validator(self, schema: Path, fixture: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--schema", str(schema), "--input", str(fixture)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_valid_recruiter_fixture_passes(self) -> None:
        result = self.run_validator(SCHEMA, FIXTURES / "valid" / "recruiter-evidence-valid.jsonl")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"valid": true', result.stdout)
        self.assertIn('"rows": 2', result.stdout)

    def test_valid_run_manifest_fixture_passes(self) -> None:
        result = self.run_validator(
            RUN_MANIFEST_SCHEMA,
            FIXTURES / "valid" / "run-manifest-valid.json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"valid": true', result.stdout)

    def test_invalid_fixtures_fail_with_expected_reason(self) -> None:
        cases = {
            "bad-citation.jsonl": "not one of",
            "missing-reference-response.jsonl": "referenceResponse",
            "unsupported-with-citation.jsonl": "expected_sources",
            "private-home-path.jsonl": "private_home_path",
            "private-email.jsonl": "email_address",
            "slack-channel-id.jsonl": "slack_channel_id",
            "malformed-jsonl.jsonl": "invalid JSON",
            "duplicate-source-labels.jsonl": "non-unique elements",
            "bad-evidence-strength.jsonl": "expected_evidence_strength",
            "extra-property.jsonl": "Additional properties",
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                result = self.run_validator(SCHEMA, FIXTURES / "invalid" / filename)
                combined = result.stdout + result.stderr
                self.assertNotEqual(result.returncode, 0, combined)
                self.assertIn("line 1", combined)
                self.assertIn(expected, combined)


if __name__ == "__main__":
    unittest.main()
