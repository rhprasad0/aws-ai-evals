#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = ROOT / "apps" / "ryanprasad-chatbot" / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from chatbot_api.eval_tools import to_bedrock_byoi_row, validate_recruiter_dataset


def _read_answers(path: Path) -> dict[str, str]:
    answers: dict[str, str] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        row_id = row.get("id") or row.get("question_id")
        answer = row.get("answer") or row.get("response")
        if not isinstance(row_id, str) or not isinstance(answer, str):
            raise ValueError(f"{path}:{line_no}: answer row needs id/question_id and answer/response")
        answers[row_id] = answer
    return answers


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert chatbot answers to Bedrock model-as-judge BYOI JSONL.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "datasets" / "synthetic" / "recruiter-evidence-qa.jsonl")
    parser.add_argument("--input", required=True, type=Path, help="Local JSONL chatbot answers. S3 URIs are documented but not read by this local adapter.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model-identifier", required=True)
    args = parser.parse_args()

    if str(args.input).startswith("s3://"):
        raise SystemExit("local adapter expects a local normalized answers JSONL file, not an S3 URI")
    rows = validate_recruiter_dataset(args.dataset)
    answers = _read_answers(args.input)
    missing = [row.id for row in rows if row.id not in answers]
    if missing:
        raise SystemExit(f"missing answer rows for ids: {missing}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(to_bedrock_byoi_row(row, response=answers[row.id], model_identifier=args.model_identifier)) + "\n")
    print({"byoi_rows": len(rows), "output": str(args.output)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
