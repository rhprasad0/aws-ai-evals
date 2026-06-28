from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import public_safety_scan


class PublicSafetyScanTests(unittest.TestCase):
    def test_public_safe_text_has_no_findings(self) -> None:
        path = Path("profile.md")
        text = "Ryan has public project evidence and no private source material here.\n"

        findings = public_safety_scan.scan_text(path, text)

        self.assertEqual([], findings)

    def test_detects_secret_shapes_and_private_context(self) -> None:
        path = Path("bad.md")
        github_token = "ghp_" + "a" * 32
        bearer = "Authorization: " + "Bearer " + "b" * 26
        home_path = "/" + "home" + "/example/.config/tool"
        private_ip = "192." + "168.1.10"
        aws_arn = "arn:" + "aws:s3:::private-bucket"
        trace_header = "x-amz-" + "request-id: abc"
        text = "\n".join(
            [
                f"token = '{github_token}'",
                bearer,
                f"private path {home_path}",
                f"private ip {private_ip}",
                f"resource {aws_arn}",
                f"trace header {trace_header}",
            ]
        )

        findings = public_safety_scan.scan_text(path, text)
        rules = {finding.rule for finding in findings}

        self.assertIn("github-token", rules)
        self.assertIn("bearer-token", rules)
        self.assertIn("home-path", rules)
        self.assertIn("private-ip", rules)
        self.assertIn("aws-arn", rules)
        self.assertIn("provider-trace-header", rules)

    def test_scan_paths_skips_unscanned_suffixes(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary_like = root / "image.bin"
            public_doc = root / "doc.md"
            binary_like.write_text("AKIA" + "A" * 16, encoding="utf-8")
            public_doc.write_text("public-safe text\n", encoding="utf-8")

            findings = public_safety_scan.scan_paths([binary_like, public_doc], root)

            self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
