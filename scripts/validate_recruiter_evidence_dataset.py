#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = ROOT / "apps" / "ryanprasad-chatbot" / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from chatbot_api.eval_tools import validate_recruiter_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate recruiter evidence JSONL fixtures.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--schema", type=Path, help="Schema path retained for CLI contract; validation is stdlib-backed.")
    args = parser.parse_args()

    try:
        rows = validate_recruiter_dataset(args.input)
    except Exception as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    print({"jsonl_valid": True, "rows": len(rows), "unique_ids": len({row.id for row in rows})})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
