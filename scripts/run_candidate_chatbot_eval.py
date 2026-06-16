#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = ROOT / "apps" / "ryanprasad-chatbot" / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from chatbot_api.eval_tools import deterministic_score, validate_recruiter_dataset


def _placeholder_response(row):
    return {
        "answer": row.referenceResponse,
        "citations": row.expected_sources,
        "evidenceStrength": row.expected_evidence_strength,
        "unsupportedClaims": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local deterministic candidate chatbot eval gates.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--mode", choices=["local-contract", "deterministic", "judge-calibration"], default="deterministic")
    parser.add_argument("--fail-on", default="citation,overclaim,private-source,refusal")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    rows = validate_recruiter_dataset(args.dataset)
    results = [deterministic_score(row, _placeholder_response(row)) for row in rows]
    failed = [result for result in results if not result.passed]
    summary = {
        "mode": args.mode,
        "rows": len(rows),
        "passed": len(rows) - len(failed),
        "failed": len(failed),
        "failures": [{"id": result.row_id, "issues": result.issues} for result in failed],
    }
    print(json.dumps(summary, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
