from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "infra" / "templates" / "bedrock-model-eval-job.json"
CUSTOM_TEMPLATE = ROOT / "infra" / "templates" / "bedrock-custom-metric-eval-job.json"


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

    def test_custom_metric_template_wires_week5_metrics_to_claude_judge(self) -> None:
        payload = json.loads(CUSTOM_TEMPLATE.read_text(encoding="utf-8"))
        automated = payload["evaluationConfig"]["automated"]
        metric_config = automated["datasetMetricConfigs"][0]
        custom_metric_config = automated["customMetricConfig"]

        self.assertEqual(payload["applicationType"], "ModelEvaluation")
        self.assertEqual(
            payload["inferenceConfig"]["models"],
            [{"precomputedInferenceSource": {"inferenceSourceIdentifier": "<BYOI_MODEL_IDENTIFIER>"}}],
        )
        self.assertEqual(
            custom_metric_config["evaluatorModelConfig"]["bedrockEvaluatorModels"],
            [{"modelIdentifier": "us.anthropic.claude-sonnet-4-6"}],
        )
        metric_names = metric_config["metricNames"]
        custom_metrics = custom_metric_config["customMetrics"]
        self.assertEqual(len(metric_names), 5)
        self.assertEqual(
            metric_names,
            [metric["customMetricDefinition"]["name"] for metric in custom_metrics],
        )
        self.assertIn("CustomMetric-CandidateCorrectness", metric_names)
        for metric in custom_metrics:
            definition = metric["customMetricDefinition"]
            self.assertIn("{{prompt}}", definition["instructions"])
            self.assertIn("{{prediction}}", definition["instructions"])
            self.assertIn("{{ground_truth}}", definition["instructions"])
            self.assertLessEqual(len(definition["instructions"]), 5000)
            self.assertEqual(
                [item["value"]["floatValue"] for item in definition["ratingScale"]],
                [0, 1, 2],
            )

    def test_custom_metric_template_contains_only_public_safe_placeholders(self) -> None:
        text = CUSTOM_TEMPLATE.read_text(encoding="utf-8")

        self.assertNotRegex(text, re.compile(r"\b\d{12}\b"))
        self.assertNotRegex(text, re.compile(r"arn:aws:[^\s\"]+"))
        self.assertIn("<BEDROCK_EVAL_ROLE_ARN>", text)
        self.assertIn("s3://example-eval-bucket/", text)


if __name__ == "__main__":
    unittest.main()
