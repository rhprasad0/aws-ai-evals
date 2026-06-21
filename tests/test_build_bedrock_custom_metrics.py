from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_bedrock_custom_metrics.py"
RUBRICS = ROOT / "rubrics"

spec = importlib.util.spec_from_file_location("build_bedrock_custom_metrics", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError("could not load custom metric builder")
builder = importlib.util.module_from_spec(spec)
sys.modules["build_bedrock_custom_metrics"] = builder
spec.loader.exec_module(builder)


class BuildBedrockCustomMetricsTests(unittest.TestCase):
    def test_build_metrics_from_all_rubrics(self) -> None:
        metrics = builder.build_metrics(RUBRICS)

        self.assertEqual(len(metrics), 5)
        self.assertEqual(
            {metric.metric_name for metric in metrics},
            {
                "CustomMetric-CandidateCorrectness",
                "CustomMetric-CandidateCompleteness",
                "CustomMetric-CandidateCitationSupport",
                "CustomMetric-CandidateRefusalAppropriateness",
                "CustomMetric-CandidateEvidenceStrengthCalibration",
            },
        )

    def test_metric_payload_has_bedrock_shape_and_variables(self) -> None:
        metric = builder.metric_from_rubric(RUBRICS / "citation-support.md")
        payload = metric.to_bedrock_definition()
        definition = payload["customMetricDefinition"]

        self.assertEqual(definition["name"], "CustomMetric-CandidateCitationSupport")
        self.assertIn("{{prompt}}", definition["instructions"])
        self.assertIn("{{prediction}}", definition["instructions"])
        self.assertIn("{{ground_truth}}", definition["instructions"])
        self.assertEqual(
            definition["ratingScale"],
            [
                {"definition": "Unsupported", "value": {"floatValue": 0}},
                {"definition": "Partially supported", "value": {"floatValue": 1}},
                {"definition": "Supported", "value": {"floatValue": 2}},
            ],
        )

    def test_cli_writes_individual_and_combined_metric_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "metrics"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--rubrics-dir",
                    str(RUBRICS),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads((output_dir / "custom-metrics.json").read_text(encoding="utf-8"))
            self.assertTrue((output_dir / "correctness.json").exists())

        self.assertEqual(len(payload["customMetrics"]), 5)
        self.assertIn("CustomMetric-CandidateCorrectness", result.stdout)


if __name__ == "__main__":
    unittest.main()
