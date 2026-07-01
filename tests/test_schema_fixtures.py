from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FIXTURES = [
    ("eval-example", ROOT / "schemas/eval-example.schema.json"),
    ("captured-response", ROOT / "schemas/captured-response.schema.json"),
    ("human-label", ROOT / "schemas/human-label.schema.json"),
    ("judge-output", ROOT / "schemas/judge-output.schema.json"),
]


class SchemaFixtureTests(unittest.TestCase):
    def test_schema_files_are_valid_draft_2020_12(self) -> None:
        for name, schema_path in SCHEMA_FIXTURES:
            with self.subTest(schema=name):
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                Draft202012Validator.check_schema(schema)

    def test_valid_fixtures_pass_and_invalid_fixtures_fail(self) -> None:
        for name, schema_path in SCHEMA_FIXTURES:
            with self.subTest(schema=name):
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                validator = Draft202012Validator(schema, format_checker=FormatChecker())
                valid = json.loads((ROOT / f"tests/fixtures/schemas/{name}.valid.json").read_text(encoding="utf-8"))
                invalid = json.loads((ROOT / f"tests/fixtures/schemas/{name}.invalid.json").read_text(encoding="utf-8"))

                valid_errors = sorted(validator.iter_errors(valid), key=lambda error: list(error.path))
                invalid_errors = sorted(validator.iter_errors(invalid), key=lambda error: list(error.path))

                self.assertEqual([], valid_errors)
                self.assertGreater(len(invalid_errors), 0)

    def test_reviewed_captured_response_jsonl_fixtures_pass(self) -> None:
        schema = json.loads((ROOT / "schemas/captured-response.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        fixture_paths = sorted((ROOT / "tests/fixtures/captured-responses").glob("*.jsonl"))

        self.assertGreater(len(fixture_paths), 0)
        for fixture_path in fixture_paths:
            with self.subTest(fixture=fixture_path.name):
                rows = [json.loads(line) for line in fixture_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                errors = [error for row in rows for error in validator.iter_errors(row)]
                rendered = json.dumps(rows)

                self.assertEqual([], errors)
                self.assertGreater(len(rows), 0)
                self.assertNotIn("ResponseMetadata", rendered)
                self.assertNotIn("requestId", rendered)
                self.assertNotIn("trace", rendered.lower())


if __name__ == "__main__":
    unittest.main()
