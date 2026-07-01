from __future__ import annotations

import json
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from jsonschema import Draft202012Validator, FormatChecker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import run_judge_smoke

ROOT = Path(__file__).resolve().parents[1]

class RunJudgeSmokeTests(unittest.TestCase):
    class FakeBedrockClient:
        def __init__(self, payload: dict) -> None:
            self.payload = payload
            self.calls = []

        def converse(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "output": {
                    "message": {
                        "content": [
                            {"text": json.dumps(self.payload)}
                        ]
                    }
                }
            }

    def test_normalize_judge_response_accepts_fenced_json_and_rejects_pass_tags(self) -> None:
        parsed = run_judge_smoke.normalize_judge_response(
            '```json\n{"predictedOutcome":"fail","failureTags":["off_contract"],"rationale":"Followed injection."}\n```'
        )

        self.assertEqual("fail", parsed["predictedOutcome"])
        self.assertEqual(["off_contract"], parsed["failureTags"])
        with self.assertRaisesRegex(ValueError, "must not include failureTags"):
            run_judge_smoke.normalize_judge_response(
                '{"predictedOutcome":"pass","failureTags":["off_contract"],"rationale":"Bad pass."}'
            )

    def test_prompt_contains_row_contract_but_not_human_label(self) -> None:
        example = run_judge_smoke.load_jsonl(ROOT / "datasets/synthetic/recruiter-evidence-qa.jsonl")[0]
        response = run_judge_smoke.load_jsonl(ROOT / "tests/fixtures/captured-responses/live-smoke-reviewed.jsonl")[0]
        profile_text = (ROOT / "profile.md").read_text(encoding="utf-8")

        prompt = run_judge_smoke.build_judge_prompt(example, response, profile_text)

        self.assertIn("expectedBehavior", prompt)
        self.assertIn("Captured Response", prompt)
        self.assertIn("predictedOutcome", prompt)
        self.assertNotIn("humanOutcome", prompt)

    def test_run_stub_judge_writes_schema_valid_output(self) -> None:
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "judge.jsonl"
            records = run_judge_smoke.run_judge(
                root=ROOT,
                examples_path=ROOT / "datasets/synthetic/recruiter-evidence-qa.jsonl",
                profile_path=ROOT / "profile.md",
                responses_path=ROOT / "tests/fixtures/captured-responses/live-smoke-reviewed.jsonl",
                output_path=output,
                judge_run_id="week6-judge-smoke-test",
                mode="stub",
                model_id="stub-judge",
                region="us-east-1",
                rubric_id="binary-profile-contract-v1",
                max_tokens=450,
                temperature=0.0,
                top_p=0.9,
                judged_at=datetime(2026, 7, 1, 15, 0, tzinfo=UTC),
            )

            schema = json.loads((ROOT / "schemas/judge-output.schema.json").read_text(encoding="utf-8"))
            validator = Draft202012Validator(schema, format_checker=FormatChecker())
            parsed = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            errors = [error for record in parsed for error in validator.iter_errors(record)]

            self.assertEqual(3, len(records))
            self.assertEqual([], errors)
            self.assertEqual("judge-output/v1", parsed[0]["schemaVersion"])
            self.assertNotIn("message", parsed[0])

    def test_bedrock_mode_uses_client_and_normalizes_output(self) -> None:
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "judge.jsonl"
            client = self.FakeBedrockClient(
                {"predictedOutcome": "pass", "failureTags": [], "rationale": "Acceptable boundary-preserving answer."}
            )
            records = run_judge_smoke.run_judge(
                root=ROOT,
                examples_path=ROOT / "datasets/synthetic/recruiter-evidence-qa.jsonl",
                profile_path=ROOT / "profile.md",
                responses_path=ROOT / "tests/fixtures/captured-responses/live-smoke-reviewed.jsonl",
                output_path=output,
                judge_run_id="week6-judge-smoke-test",
                mode="bedrock",
                model_id="us.anthropic.claude-sonnet-4-6",
                region="us-east-1",
                rubric_id="binary-profile-contract-v1",
                max_tokens=450,
                temperature=0.0,
                top_p=0.9,
                limit=1,
                judged_at=datetime(2026, 7, 1, 15, 0, tzinfo=UTC),
                bedrock_client=client,
            )

            self.assertEqual(1, len(records))
            self.assertEqual("pass", records[0]["predictedOutcome"])
            self.assertEqual(1, len(client.calls))
            self.assertEqual("us.anthropic.claude-sonnet-4-6", client.calls[0]["modelId"])

    def test_compare_reports_false_passes_false_fails_and_tag_drift(self) -> None:
        labels = [
            {"schemaVersion": "human-label/v1", "exampleId": "row-a", "runId": "run", "humanOutcome": "fail", "failureTags": ["off_contract"]},
            {"schemaVersion": "human-label/v1", "exampleId": "row-b", "runId": "run", "humanOutcome": "pass"},
            {"schemaVersion": "human-label/v1", "exampleId": "row-c", "runId": "run", "humanOutcome": "fail", "failureTags": ["off_contract"]},
        ]
        judge_outputs = [
            {"exampleId": "row-a", "predictedOutcome": "pass", "failureTags": [], "rationale": "Missed failure."},
            {"exampleId": "row-b", "predictedOutcome": "fail", "failureTags": ["too_vague"], "rationale": "Overstrict."},
            {"exampleId": "row-c", "predictedOutcome": "fail", "failureTags": ["wrong_refusal"], "rationale": "Wrong tag."},
        ]

        comparison = run_judge_smoke.compare_judge_to_labels(judge_outputs, labels)

        self.assertEqual([], comparison.failures)
        self.assertEqual(3, comparison.summary["compared"])
        self.assertEqual(1, len(comparison.summary["falsePasses"]))
        self.assertEqual(1, len(comparison.summary["falseFails"]))
        self.assertEqual(1, len(comparison.summary["tagDrift"]))

if __name__ == "__main__":
    unittest.main()
