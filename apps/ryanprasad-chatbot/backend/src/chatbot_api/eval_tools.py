from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .response_contract import ALLOWED_EVIDENCE_STRENGTHS, ALLOWED_SOURCE_LABELS, ResponseContractError, validate_chat_response

REQUIRED_RECRUITER_FIELDS = {
    "id",
    "question",
    "expected_sources",
    "must_include",
    "must_not_claim",
    "expected_evidence_strength",
    "referenceResponse",
    "category",
}


@dataclass(frozen=True)
class RecruiterEvalRow:
    id: str
    question: str
    expected_sources: list[str]
    must_include: list[str]
    must_not_claim: list[str]
    expected_evidence_strength: str
    referenceResponse: str
    category: str


@dataclass(frozen=True)
class ScoreResult:
    row_id: str
    passed: bool
    issues: list[str]


def _require_string_list(row: dict[str, Any], key: str, *, line_no: int) -> list[str]:
    value = row.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"line {line_no}: {key} must be a list of strings")
    return value


def row_from_dict(row: dict[str, Any], *, line_no: int) -> RecruiterEvalRow:
    missing = REQUIRED_RECRUITER_FIELDS - row.keys()
    if missing:
        raise ValueError(f"line {line_no}: missing required fields: {sorted(missing)}")
    for key in ["id", "question", "expected_evidence_strength", "referenceResponse", "category"]:
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError(f"line {line_no}: {key} must be a non-empty string")
    expected_sources = _require_string_list(row, "expected_sources", line_no=line_no)
    unknown_sources = sorted(set(expected_sources) - ALLOWED_SOURCE_LABELS)
    if unknown_sources:
        raise ValueError(f"line {line_no}: expected_sources contain unknown labels: {unknown_sources}")
    evidence_strength = row["expected_evidence_strength"]
    if evidence_strength not in ALLOWED_EVIDENCE_STRENGTHS:
        raise ValueError(f"line {line_no}: expected_evidence_strength is not allowed: {evidence_strength}")
    return RecruiterEvalRow(
        id=row["id"],
        question=row["question"],
        expected_sources=expected_sources,
        must_include=_require_string_list(row, "must_include", line_no=line_no),
        must_not_claim=_require_string_list(row, "must_not_claim", line_no=line_no),
        expected_evidence_strength=evidence_strength,
        referenceResponse=row["referenceResponse"],
        category=row["category"],
    )


def validate_recruiter_dataset(path: Path) -> list[RecruiterEvalRow]:
    rows: list[RecruiterEvalRow] = []
    ids: set[str] = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_no}: invalid JSON: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"line {line_no}: row must be a JSON object")
        row = row_from_dict(payload, line_no=line_no)
        if row.id in ids:
            raise ValueError(f"line {line_no}: duplicate id: {row.id}")
        ids.add(row.id)
        rows.append(row)
    if not rows:
        raise ValueError("dataset has no rows")
    return rows


def deterministic_score(row: RecruiterEvalRow, response_payload: dict[str, Any]) -> ScoreResult:
    issues: list[str] = []
    try:
        response = validate_chat_response(response_payload)
    except ResponseContractError as exc:
        return ScoreResult(row_id=row.id, passed=False, issues=[str(exc)])

    lower_answer = response.answer.lower()
    citation_set = set(response.citations)
    for expected_source in row.expected_sources:
        if expected_source not in citation_set:
            issues.append(f"missing expected source: {expected_source}")
    for phrase in row.must_include:
        if not _contains_required_phrase(lower_answer, phrase.lower()):
            issues.append(f"missing required phrase: {phrase}")
    for phrase in row.must_not_claim:
        if _contains_unnegated_forbidden_phrase(lower_answer, phrase.lower()):
            issues.append(f"contains forbidden claim: {phrase}")
    if response.evidenceStrength != row.expected_evidence_strength:
        issues.append(
            f"wrong evidence strength: expected {row.expected_evidence_strength}, got {response.evidenceStrength}"
        )
    return ScoreResult(row_id=row.id, passed=not issues, issues=issues)


def _contains_required_phrase(answer: str, phrase: str) -> bool:
    if phrase in answer:
        return True
    if phrase == "not supported" and "does not support" in answer:
        return True
    if phrase == "not supported" and "no evidence" in answer:
        return True
    if phrase == "public evidence" and "public facts" in answer:
        return True
    if phrase == "public source" and "public facts" in answer:
        return True
    return False


def _contains_unnegated_forbidden_phrase(answer: str, phrase: str) -> bool:
    start = answer.find(phrase)
    if start == -1:
        return False
    prefix = answer[max(0, start - 80):start]
    negators = (
        "not ",
        "does not support",
        "do not support",
        "not support",
        "no evidence",
        "without evidence",
        "unsupported",
    )
    return not any(negator in prefix for negator in negators)


def to_bedrock_byoi_row(row: RecruiterEvalRow, *, response: str, model_identifier: str) -> dict[str, Any]:
    if not model_identifier.strip():
        raise ValueError("model_identifier must be non-empty")
    return {
        "prompt": row.question,
        "referenceResponse": row.referenceResponse,
        "category": row.category,
        "modelResponses": [
            {
                "response": response,
                "modelIdentifier": model_identifier,
            }
        ],
    }
