#!/usr/bin/env python3
"""Scan public repo artifacts for obvious secrets, private identifiers, and raw traces."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SCANNED_SUFFIXES = {
    ".md",
    ".json",
    ".jsonl",
    ".py",
    ".yml",
    ".yaml",
    ".txt",
}

DEFAULT_EXCLUDE_PARTS = {
    ".git",
    ".hermes",
    "__pycache__",
    ".pytest_cache",
}


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str
    excerpt: str

    def render(self, root: Path) -> str:
        try:
            display_path = self.path.relative_to(root)
        except ValueError:
            display_path = self.path
        return f"{display_path}:{self.line}: {self.rule}: {self.excerpt}"


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    description: str


TRACE_HEADER_PATTERN = "|".join(["x-amz-" + "request-id", "x-amzn-" + "requestid", "trace" + "parent"])

RULES = [
    Rule("private-key-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key material"),
    Rule("aws-access-key-id", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    Rule("aws-secret-assignment", re.compile(r"(?i)\baws_secret_access_key\b\s*[:=]\s*[\"']?[A-Za-z0-9/+=]{20,}"), "AWS secret assignment"),
    Rule("aws-arn", re.compile(r"\barn:aws[a-z-]*:[^\s\"'`,]+"), "AWS ARN or resource identifier"),
    Rule("aws-account-id", re.compile(r"(?<![\w-])\d{12}(?![\w-])"), "12-digit AWS-style account id"),
    Rule("bearer-token", re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+[A-Za-z0-9._~+/-]{10,}"), "bearer token"),
    Rule("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "GitHub token"),
    Rule("openai-token", re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{18,}\b"), "OpenAI-style token"),
    Rule("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"), "Slack token"),
    Rule("home-path", re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+(?:/|\b)"), "private local home path"),
    Rule("private-ip", re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b"), "private network IP"),
    Rule("private-hostname", re.compile(r"\b[A-Za-z0-9][A-Za-z0-9.-]*\.(?:lan|internal|corp)\b"), "private hostname"),
    Rule("provider-trace-header", re.compile(rf"(?i)\b(?:{TRACE_HEADER_PATTERN})\b"), "provider/request trace header"),
    Rule("raw-provider-json-key", re.compile(r"(?i)[\"'](?:raw_response|raw_provider_response|provider_trace|bedrock_trace)[\"']\s*:"), "raw provider response or trace field"),
]


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [root / line for line in result.stdout.splitlines() if line]


def should_scan(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path
    if any(part in DEFAULT_EXCLUDE_PARTS for part in relative.parts):
        return False
    return path.suffix in SCANNED_SUFFIXES


def safe_excerpt(line: str, match: re.Match[str]) -> str:
    start = max(match.start() - 24, 0)
    end = min(match.end() + 24, len(line))
    excerpt = line[start:end].strip()
    if len(excerpt) > 120:
        excerpt = excerpt[:117] + "..."
    return excerpt


def scan_text(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule in RULES:
            match = rule.pattern.search(line)
            if match:
                findings.append(Finding(path, line_number, rule.name, safe_excerpt(line, match)))
    return findings


def scan_paths(paths: list[Path], root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        if not should_scan(path, root):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            continue
        findings.extend(scan_text(path, text))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan tracked public artifacts for secrets and private data.")
    parser.add_argument("paths", nargs="*", type=Path, help="Optional file paths to scan instead of git-tracked files")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    if args.paths:
        paths = [path if path.is_absolute() else root / path for path in args.paths]
    else:
        paths = tracked_files(root)
    findings = scan_paths(paths, root)
    if findings:
        print(f"FAIL: {len(findings)} public-safety finding(s)", file=sys.stderr)
        for finding in findings:
            print(finding.render(root), file=sys.stderr)
        return 1
    print(f"OK: scanned {sum(1 for path in paths if should_scan(path, root))} public artifact(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
