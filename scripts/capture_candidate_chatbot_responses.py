#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = ROOT / "apps" / "ryanprasad-chatbot" / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from chatbot_api.eval_tools import RecruiterEvalRow, deterministic_score, validate_recruiter_dataset
from chatbot_api.response_contract import ResponseContractError, validate_chat_response

DEFAULT_ENDPOINT = "https://chat.ryans-lab.click/api/chat"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture live/local candidate-chatbot responses, validate response contracts, and run deterministic scoring."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "datasets" / "synthetic" / "recruiter-evidence-qa.jsonl",
        help="Recruiter evidence JSONL dataset to replay.",
    )
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Chat endpoint URL, usually ending in /api/chat.")
    parser.add_argument("--output", required=True, type=Path, help="Normalized captured responses JSONL output path.")
    parser.add_argument("--ids", help="Comma-separated row ids to replay. Defaults to all rows.")
    parser.add_argument("--limit", type=int, help="Maximum rows to replay after id filtering.")
    parser.add_argument("--session-prefix", default=f"eval-capture-{int(time.time())}")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.0, help="Optional delay between endpoint calls.")
    parser.add_argument("--fail-on-score", action="store_true", help="Exit non-zero when deterministic scoring fails.")
    parser.add_argument("--fail-on-request", action="store_true", help="Exit non-zero when an endpoint request fails.")
    return parser.parse_args()


def select_rows(rows: list[RecruiterEvalRow], *, ids: str | None, limit: int | None) -> list[RecruiterEvalRow]:
    selected = rows
    if ids:
        wanted = [item.strip() for item in ids.split(",") if item.strip()]
        by_id = {row.id: row for row in rows}
        missing = [row_id for row_id in wanted if row_id not in by_id]
        if missing:
            raise ValueError(f"unknown dataset ids: {missing}")
        selected = [by_id[row_id] for row_id in wanted]
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be >= 1")
        selected = selected[:limit]
    return selected


def request_payload(row: RecruiterEvalRow, *, session_prefix: str) -> dict[str, Any]:
    return {
        "sessionId": f"{session_prefix}-{row.id}",
        "messages": [{"role": "user", "content": row.question}],
    }


def post_chat(endpoint: str, payload: dict[str, Any], *, timeout_seconds: float) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = int(response.status)
            data = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        data = exc.read().decode("utf-8", errors="replace")
    payload = json.loads(data) if data.strip() else {}
    if not isinstance(payload, dict):
        raise ValueError("endpoint response must be a JSON object")
    return status, payload


def capture_row(row: RecruiterEvalRow, *, endpoint: str, session_prefix: str, timeout_seconds: float) -> dict[str, Any]:
    request = request_payload(row, session_prefix=session_prefix)
    try:
        status_code, response_payload = post_chat(endpoint, request, timeout_seconds=timeout_seconds)
    except Exception as exc:
        return {
            "id": row.id,
            "question": row.question,
            "request": request,
            "httpStatus": None,
            "responseValid": False,
            "scorePassed": False,
            "error": f"request_failed: {exc}",
        }

    normalized: dict[str, Any] = {
        "id": row.id,
        "question": row.question,
        "request": request,
        "httpStatus": status_code,
        "rawResponse": response_payload,
    }
    try:
        response = validate_chat_response(response_payload)
    except ResponseContractError as exc:
        normalized.update(
            {
                "responseValid": False,
                "scorePassed": False,
                "error": f"response_contract_failed: {exc}",
            }
        )
        return normalized

    response_dict = response.to_dict()
    score = deterministic_score(row, response_dict)
    normalized.update(
        {
            "answer": response.answer,
            "citations": response.citations,
            "evidenceStrength": response.evidenceStrength,
            "unsupportedClaims": response.unsupportedClaims,
            "responseValid": True,
            "scorePassed": score.passed,
            "scoreIssues": score.issues,
        }
    )
    return normalized


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rows": len(rows),
        "response_valid": sum(1 for row in rows if row.get("responseValid")),
        "score_passed": sum(1 for row in rows if row.get("scorePassed")),
        "request_failed": sum(1 for row in rows if row.get("error", "").startswith("request_failed")),
        "failures": [
            {
                "id": row.get("id"),
                "httpStatus": row.get("httpStatus"),
                "error": row.get("error"),
                "scoreIssues": row.get("scoreIssues"),
            }
            for row in rows
            if row.get("error") or not row.get("scorePassed")
        ],
    }


def main() -> int:
    args = parse_args()
    try:
        rows = select_rows(validate_recruiter_dataset(args.dataset), ids=args.ids, limit=args.limit)
    except Exception as exc:
        print(f"capture failed: {exc}", file=sys.stderr)
        return 1

    captured: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        captured.append(
            capture_row(
                row,
                endpoint=args.endpoint,
                session_prefix=args.session_prefix,
                timeout_seconds=args.timeout_seconds,
            )
        )
        if args.sleep_seconds and index < len(rows) - 1:
            time.sleep(args.sleep_seconds)

    write_jsonl(args.output, captured)
    summary = summarize(captured)
    summary["output"] = str(args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.fail_on_request and summary["request_failed"]:
        return 1
    if args.fail_on_score and summary["score_passed"] != summary["rows"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
