from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "infra" / "templates" / "bedrock-model-eval-job.json"


class BedrockEvalJobTemplateTests(unittest.TestCase):
    def test_template_uses_byoi_precomputed_inference_source(self) -> None:
        payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))

        self.assertEqual(payload["applicationType"], "ModelEvaluation")
        self.assertEqual(
            payload["inferenceConfig"]["models"],
            [{"precomputedInferenceSource": {"inferenceSourceIdentifier": "<BYOI_MODEL_IDENTIFIER>"}}],
        )
        metric_config = payload["evaluationConfig"]["automated"]["datasetMetricConfigs"][0]
        self.assertEqual(metric_config["taskType"], "General")
        self.assertEqual(metric_config["dataset"]["datasetLocation"]["s3Uri"], "s3://example-eval-bucket/input/bedrock-model-eval-byoi.jsonl")
        self.assertEqual(metric_config["metricNames"], ["Builtin.Correctness", "Builtin.Completeness"])

    def test_template_contains_only_public_safe_placeholders(self) -> None:
        text = TEMPLATE.read_text(encoding="utf-8")

        self.assertNotRegex(text, re.compile(r"\b\d{12}\b"))
        self.assertNotRegex(text, re.compile(r"arn:aws:[^\s\"]+"))
        self.assertIn("<BEDROCK_EVAL_ROLE_ARN>", text)
        self.assertIn("s3://example-eval-bucket/", text)


if __name__ == "__main__":
    unittest.main()
