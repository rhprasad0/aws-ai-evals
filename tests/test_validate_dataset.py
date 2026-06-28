from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import validate_dataset


ROOT = Path(__file__).resolve().parents[1]


class ValidateDatasetTests(unittest.TestCase):
    def test_repo_validation_passes(self) -> None:
        messages, failures = validate_dataset.validate_repo(ROOT)

        self.assertEqual([], failures)
        self.assertIn("OK: 3 schemas are valid Draft 2020-12 JSON Schemas", messages)
        self.assertIn("OK: 6 schema fixtures behaved as expected", messages)
        self.assertTrue(any(message.startswith("OK: 18 rows validated") for message in messages))

    def test_jsonl_failure_reports_line_and_schema_path(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_path = root / "schemas"
            schema_path.mkdir()
            schema = json.loads((ROOT / "schemas/eval-example.schema.json").read_text(encoding="utf-8"))
            (schema_path / "eval-example.schema.json").write_text(json.dumps(schema), encoding="utf-8")
            dataset_path = root / "bad.jsonl"
            dataset_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": "eval-example/v1",
                        "exampleId": "bad-row-001",
                        "question": "Short?",
                        "requestClass": "unsupported_or_overclaim",
                        "expectedBehavior": "say_not_supported",
                        "sourceSupport": "unsupported",
                        "expectedAnswerNotes": "Missing productionAiProbe should fail.",
                    }
                )
                + "\n{bad json}\n",
                encoding="utf-8",
            )

            loaded_schema, schema_failures = validate_dataset.load_schema(root, "eval-example")
            self.assertEqual([], schema_failures)
            self.assertIsNotNone(loaded_schema)
            validator = validate_dataset.Draft202012Validator(
                loaded_schema,
                format_checker=validate_dataset.FormatChecker(),
            )
            _, failures = validate_dataset.validate_jsonl_file(dataset_path, validator)
            rendered = "\n".join(failure.render(root) for failure in failures)

            self.assertIn("bad.jsonl:1", rendered)
            self.assertIn("productionAiProbe", rendered)
            self.assertIn("schema_path=/required", rendered)
            self.assertIn("bad.jsonl:2", rendered)
            self.assertIn("invalid JSONL row", rendered)

    def test_duplicate_example_id_is_reported(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_dir = root / "schemas"
            schema_dir.mkdir()
            schema = json.loads((ROOT / "schemas/eval-example.schema.json").read_text(encoding="utf-8"))
            (schema_dir / "eval-example.schema.json").write_text(json.dumps(schema), encoding="utf-8")
            row = json.loads((ROOT / "tests/fixtures/schemas/eval-example.valid.json").read_text(encoding="utf-8"))
            dataset_path = root / "duplicate.jsonl"
            dataset_path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")

            loaded_schema, schema_failures = validate_dataset.load_schema(root, "eval-example")
            self.assertEqual([], schema_failures)
            self.assertIsNotNone(loaded_schema)
            validator = validate_dataset.Draft202012Validator(loaded_schema)
            _, failures = validate_dataset.validate_jsonl_file(dataset_path, validator)

            self.assertTrue(any("duplicate exampleId" in failure.message for failure in failures))

    def test_display_path_accepts_files_outside_repo_root(self) -> None:
        outside = Path("/tmp/example.json")

        self.assertEqual(outside, validate_dataset.display_path(outside, ROOT))


if __name__ == "__main__":
    unittest.main()
