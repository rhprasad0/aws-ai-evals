from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "score_app_events.py"
SCHEMA = ROOT / "schemas" / "aws-evals" / "normalized-app-event.schema.json"

spec = importlib.util.spec_from_file_location("score_app_events", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError("could not load score script")
scorer = importlib.util.module_from_spec(spec)
sys.modules["score_app_events"] = scorer
spec.loader.exec_module(scorer)


def bedrock_event(**overrides):
    event = {
        "schema_version": "normalized-app-event/v1",
        "event": "chat_response_completed",
        "response_source": "bedrock",
        "request_class": "chat",
        "prompt_template_version": "candidate-evidence-v1",
        "model_id": "us.amazon.nova-2-lite-v1:0",
        "max_tokens": 768,
        "citation_labels": ["aws-devops-lab README"],
        "citation_count": 1,
        "evidence_strength": "medium_high_lab_project",
        "unsupported_claim_count": 0,
        "elapsed_ms": 1200,
        "input_tokens": 100,
        "output_tokens": 25,
        "total_tokens": 125,
    }
    event.update(overrides)
    return event


def guardrail_event(**overrides):
    event = {
        "schema_version": "normalized-app-event/v1",
        "event": "chat_response_completed",
        "response_source": "guardrail",
        "request_class": "chat",
        "prompt_template_version": "candidate-evidence-v1",
        "model_id": "us.amazon.nova-2-lite-v1:0",
        "max_tokens": 768,
        "citation_labels": [],
        "citation_count": 0,
        "evidence_strength": "unsupported_private",
        "unsupported_claim_count": 1,
    }
    event.update(overrides)
    return event


class ScoreAppEventsTests(unittest.TestCase):
    def test_score_events_passes_valid_bedrock_and_guardrail_events(self) -> None:
        schema = scorer.load_schema(SCHEMA)
        events = [bedrock_event(), guardrail_event()]

        scores = scorer.score_events(events, schema=schema, max_latency_ms=5000, max_total_tokens=4000)
        summary = scorer.summarize(events, scores)

        self.assertEqual(summary["passed"], 2)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["response_sources"], {"bedrock": 1, "guardrail": 1})

    def test_score_event_flags_budget_and_token_mismatches(self) -> None:
        issues = scorer.score_event(
            bedrock_event(elapsed_ms=9000, input_tokens=100, output_tokens=25, total_tokens=200),
            max_latency_ms=5000,
            max_total_tokens=150,
        )

        self.assertIn("latency budget exceeded: 9000ms > 5000ms", issues)
        self.assertIn("token total mismatch: input_tokens + output_tokens = 125, got 200", issues)
        self.assertIn("token budget exceeded: 200 > 150", issues)

    def test_score_event_flags_supported_event_without_citations(self) -> None:
        issues = scorer.score_event(
            bedrock_event(citation_labels=[], citation_count=0),
            max_latency_ms=5000,
            max_total_tokens=4000,
        )

        self.assertIn("supported event must include at least one citation", issues)

    def test_schema_validation_blocks_leaky_answer_field(self) -> None:
        schema = scorer.load_schema(SCHEMA)
        events = [bedrock_event(answer="raw answer should not be in app-event exports")]

        scores = scorer.score_events(events, schema=schema, max_latency_ms=5000, max_total_tokens=4000)

        self.assertFalse(scores[0].passed)
        self.assertIn("Additional properties", scores[0].issues[0])

    def test_cli_scores_jsonl_and_fails_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(json.dumps(bedrock_event(elapsed_ms=9000)) + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(path), "--fail-on-score"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn('"failed": 1', result.stdout)
        self.assertIn("latency budget exceeded", result.stdout)


if __name__ == "__main__":
    unittest.main()
