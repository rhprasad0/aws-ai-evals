#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
SKIP_DIRS = {".git", ".venv", "node_modules", "raw-data", "traces", "results", "scratch", "agent-prompts", "agent-outputs"}
TEXT_EXTS = {".md", ".py", ".txt", ".yml", ".yaml", ".json", ".toml", ".gitignore"}
PATTERNS = {
    "private_home_path": re.compile(r"/home/[A-Za-z0-9._-]+"),
    "slack_channel_id": re.compile(r"\bC0[A-Z0-9]{8,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "secret_token": re.compile(r"\b(?:sk|gh[pousr]|xox[baprs])-[-A-Za-z0-9_]{16,}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    "likely_internal_ip": re.compile(
        r"\b(?:10\.\d{1,3}|172\.(?:1[6-9]|2[0-9]|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b"
    ),
}
ALLOW = [
    "A[K]IA",
    "example.com",
]

bad: list[str] = []
for path in ROOT.rglob("*"):
    if path.is_dir():
        continue
    rel = path.relative_to(ROOT)
    if any(part in SKIP_DIRS for part in rel.parts):
        continue
    if path.suffix not in TEXT_EXTS and path.name != ".gitignore":
        continue
    try:
        text = path.read_text(errors="replace")
    except Exception:
        continue
    for name, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            line = text.splitlines()[line_no - 1]
            if any(token in line for token in ALLOW):
                continue
            bad.append(f"{rel}:{line_no}: {name}: {line.strip()[:160]}")

if bad:
    print("Public-safety scan failed:")
    print("\n".join(bad))
    sys.exit(1)
print("Public-safety scan passed")
