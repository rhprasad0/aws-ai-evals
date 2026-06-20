from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "apps" / "ryanprasad-chatbot" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from chatbot_api.eval_tools import RecruiterEvalRow, to_bedrock_byoi_row, validate_recruiter_dataset  # type: ignore[import-not-found]


@dataclass(frozen=True)
class CapturedAnswer:
    row_id: str
    response: str
    source_line: int


def _load_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_no}: row must be a JSON object")
        yield line_no, payload


def captured_answer_from_row(row: dict[str, Any], *, line_no: int, require_valid_response: bool = True) -> CapturedAnswer:
    row_id = row.get("id") or row.get("question_id")
    if not isinstance(row_id, str) or not row_id.strip():
        raise ValueError(f"line {line_no}: answer row needs a non-empty id or question_id")

    if require_valid_response and row.get("responseValid") is False:
        raise ValueError(f"line {line_no}: answer row {row_id} has responseValid=false")

    answer = row.get("answer") or row.get("response")
    if not isinstance(answer, str) or not answer.strip():
        raw_response = row.get("rawResponse")
        if isinstance(raw_response, dict):
            answer = raw_response.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(f"line {line_no}: answer row {row_id} needs a non-empty answer/response")

    return CapturedAnswer(row_id=row_id, response=answer, source_line=line_no)


def read_captured_answers(path: Path, *, require_valid_response: bool = True) -> dict[str, CapturedAnswer]:
    answers: dict[str, CapturedAnswer] = {}
    for line_no, payload in _load_jsonl(path):
        answer = captured_answer_from_row(payload, line_no=line_no, require_valid_response=require_valid_response)
        if answer.row_id in answers:
            previous = answers[answer.row_id].source_line
            raise ValueError(f"{path}:{line_no}: duplicate answer id {answer.row_id}; first seen on line {previous}")
        answers[answer.row_id] = answer
    if not answers:
        raise ValueError(f"{path}: captured answers file has no rows")
    return answers


def build_byoi_rows(
    dataset_rows: list[RecruiterEvalRow],
    answers: dict[str, CapturedAnswer],
    *,
    model_identifier: str,
) -> list[dict[str, Any]]:
    if not model_identifier.strip():
        raise ValueError("model_identifier must be non-empty")
    missing = [row.id for row in dataset_rows if row.id not in answers]
    if missing:
        raise ValueError(f"missing answer rows for ids: {missing}")
    return [
        to_bedrock_byoi_row(row, response=answers[row.id].response, model_identifier=model_identifier)
        for row in dataset_rows
    ]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            count += 1
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return count


def convert_captured_answers_to_byoi(
    *,
    dataset_path: Path,
    input_path: Path,
    output_path: Path,
    model_identifier: str,
    require_valid_response: bool = True,
) -> dict[str, Any]:
    if str(input_path).startswith("s3://"):
        raise ValueError("local adapter expects a local normalized answers JSONL file, not an S3 URI")
    dataset_rows = validate_recruiter_dataset(dataset_path)
    answers = read_captured_answers(input_path, require_valid_response=require_valid_response)
    byoi_rows = build_byoi_rows(dataset_rows, answers, model_identifier=model_identifier)
    count = write_jsonl(output_path, byoi_rows)
    return {
        "byoi_rows": count,
        "dataset_rows": len(dataset_rows),
        "input_rows": len(answers),
        "model_identifier": model_identifier,
        "output": str(output_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert captured chatbot answers to Bedrock model-as-judge BYOI JSONL.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "datasets" / "synthetic" / "recruiter-evidence-qa.jsonl",
        help="Recruiter evidence dataset used to produce the captured answers.",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Local JSONL captured answers from scripts/capture_candidate_chatbot_responses.py.",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model-identifier", required=True)
    parser.add_argument(
        "--allow-invalid-captures",
        action="store_true",
        help="Allow rows with responseValid=false if they still contain a usable answer. Deterministic score failures are always allowed.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = convert_captured_answers_to_byoi(
            dataset_path=args.dataset,
            input_path=args.input,
            output_path=args.output,
            model_identifier=args.model_identifier,
            require_valid_response=not args.allow_invalid_captures,
        )
    except Exception as exc:
        print(f"BYOI adapter failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
