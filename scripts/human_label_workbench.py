#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "datasets" / "synthetic" / "recruiter-evidence-qa.jsonl"
DEFAULT_LABELS = ROOT / "datasets" / "synthetic" / "human-labels.jsonl"
DEFAULT_ARCHIVE_DIR = ROOT / "build" / "human-labeling"
DEFAULT_DRAFT = DEFAULT_ARCHIVE_DIR / "draft-label-state.json"
HUMAN_LABEL_SCHEMA = ROOT / "schemas" / "human-label.schema.json"
RECRUITER_DATASET_SCHEMA = ROOT / "schemas" / "recruiter-evidence-qa.schema.json"
VALIDATOR = ROOT / "scripts" / "validate_dataset.py"
SOURCE_DATASET = "datasets/synthetic/recruiter-evidence-qa.jsonl"
DATASET_ROW_KEYS = (
    "id",
    "question",
    "expected_sources",
    "must_include",
    "must_not_claim",
    "expected_evidence_strength",
    "referenceResponse",
    "category",
)

RUBRIC_VERSIONS = {
    "correctness": "candidate-correctness/v1",
    "completeness": "candidate-completeness/v1",
    "citation_support": "candidate-citation-support/v1",
    "refusal_appropriateness": "candidate-refusal-appropriateness/v1",
    "evidence_strength_calibration": "candidate-evidence-strength/v1",
}
RUBRIC_ORDER = tuple(RUBRIC_VERSIONS)

SCORE_LABELS = {0: "fail", 1: "partial", 2: "pass"}
SCORE_EXPLANATIONS = {
    0: "Fail: material rubric violation such as unsupported claims, bad citations, refusal mistakes, private-source leakage, or major omissions.",
    1: "Partial: directionally right but incomplete, weakly supported, imprecise, or missing a material caveat.",
    2: "Pass: satisfies this rubric; any caveat is minor and does not change the judgment.",
}

EXPECTED_OUTCOMES = (
    "answered_from_public_evidence",
    "unsupported_public_claim",
    "unsupported_private_source",
    "off_scope",
    "prompt_injection_ignored",
    "rate_limited",
    "needs_human_review",
)
OUTCOME_EXPLANATIONS = {
    "answered_from_public_evidence": "Answer is supported by allowed public evidence.",
    "unsupported_public_claim": "Question asks for a public claim that the allowed evidence does not support.",
    "unsupported_private_source": "Question would require private, non-public, or excluded source material.",
    "off_scope": "Question is outside the chatbot's intended candidate-evidence scope.",
    "prompt_injection_ignored": "Prompt attempted instruction override or source manipulation and the answer ignored it.",
    "rate_limited": "Repeated/abusive behavior should be limited rather than answered normally.",
    "needs_human_review": "The case is ambiguous enough that a human should review it before treating it as truth.",
}

EVIDENCE_STRENGTHS = (
    "high_public_project",
    "medium_high_public_project",
    "medium_high_lab_project",
    "calibration_required",
    "weak_support",
    "unsupported",
    "unsupported_private",
)
EVIDENCE_STRENGTH_EXPLANATIONS = {
    "high_public_project": "Strong public project evidence directly supports the claim.",
    "medium_high_public_project": "Good public project evidence supports the claim, with normal public-project caveats.",
    "medium_high_lab_project": "Lab or demo evidence supports the claim, but not production ownership.",
    "calibration_required": "Support level needs careful human calibration before being used as a confident label.",
    "weak_support": "Evidence is thin, indirect, or only partially related.",
    "unsupported": "Allowed public evidence does not support the claim.",
    "unsupported_private": "Claim would depend on private or excluded evidence.",
}

FAILURE_LABELS = (
    "unsupported_claim",
    "citation_missing",
    "citation_invalid",
    "citation_does_not_support_claim",
    "evidence_strength_overstated",
    "evidence_strength_understated",
    "private_source_claim",
    "over_refusal",
    "under_refusal",
    "material_omission",
    "schema_or_parse_issue",
    "high_variance_candidate",
)
FAILURE_LABEL_EXPLANATIONS = {
    "unsupported_claim": "Answer makes a material claim not supported by the allowed evidence.",
    "citation_missing": "A material supported claim needs a citation/source label but lacks one.",
    "citation_invalid": "Citation/source label is unknown, malformed, private, or not allowed.",
    "citation_does_not_support_claim": "Citation exists but does not actually support the attached claim.",
    "evidence_strength_overstated": "Answer or label upgrades support beyond what the evidence warrants.",
    "evidence_strength_understated": "Answer or label is too conservative for the available evidence.",
    "private_source_claim": "Answer relies on or implies private-source support.",
    "over_refusal": "Answer refuses or over-caveats when it should answer from public evidence.",
    "under_refusal": "Answer responds when it should refuse, caveat, or redirect.",
    "material_omission": "Answer leaves out a required or important piece of the response.",
    "schema_or_parse_issue": "Response has contract/schema/parse problems that affect judgment.",
    "high_variance_candidate": "Case is a known high-variance candidate for repeated judge review.",
}

RUBRIC_EXPLANATIONS = {
    "correctness": "Are the answer's material claims factually supported by the allowed evidence?",
    "completeness": "Does the answer cover the requested evidence boundary without omitting key required pieces?",
    "citation_support": "Do the provided citations/source labels actually support the claims they attach to?",
    "refusal_appropriateness": "Does the answer choose the right action: answer, refuse, caveat, or ignore injection?",
    "evidence_strength_calibration": "Does the answer use the right evidence-strength label and matching caveat?",
}


@dataclass
class LabelSlot:
    example_id: str
    rubric_id: str
    source_dataset: str = SOURCE_DATASET
    score: int | None = None
    expected_outcome: str | None = None
    expected_evidence_strength: str | None = None
    expected_failure_labels: list[str] = field(default_factory=list)
    human_rationale: str = ""
    label_version: str = "v1"

    @property
    def key(self) -> tuple[str, str]:
        return (self.example_id, self.rubric_id)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[1:]
    if not argv or argv[0] not in {"gui", "clear", "validate", "-h", "--help"}:
        argv = ["gui", *argv]
    parser = argparse.ArgumentParser(description="GUI and CLI helpers for Week 5 human labels.")
    subparsers = parser.add_subparsers(dest="command")

    gui = subparsers.add_parser("gui", help="Open the Tkinter human-label workbench.")
    gui.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    gui.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    gui.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    gui.add_argument("--byoi-jsonl", type=Path)
    gui.add_argument("--captured-jsonl", type=Path)
    gui.add_argument("--host", default="127.0.0.1", help="Host for browser fallback when Tkinter is unavailable.")
    gui.add_argument("--port", type=int, default=8765, help="Port for browser fallback when Tkinter is unavailable.")

    clear = subparsers.add_parser("clear", help="Archive and empty the human-label JSONL file.")
    clear.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    clear.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR)

    validate = subparsers.add_parser("validate", help="Validate completeness and schema shape of final labels.")
    validate.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    validate.add_argument("--labels", type=Path, default=DEFAULT_LABELS)

    return parser.parse_args(argv)


def repo_rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def load_jsonl(path: Path, *, allow_empty: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        if allow_empty:
            return []
        raise ValueError(f"{path}: does not exist")
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: line {line_no}: invalid JSON at column {exc.colno}: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"{path}: line {line_no}: row must be a JSON object")
        rows.append(payload)
    if not rows and not allow_empty:
        raise ValueError(f"{path}: contains no JSON objects")
    return rows


def load_examples(path: Path) -> list[dict[str, Any]]:
    rows = load_jsonl(path)
    seen: set[str] = set()
    for row in rows:
        example_id = str(row.get("id", ""))
        if not example_id:
            raise ValueError(f"{path}: dataset row missing id")
        if example_id in seen:
            raise ValueError(f"{path}: duplicate example id {example_id}")
        seen.add(example_id)
    return rows


def source_label_options(schema_path: Path = RECRUITER_DATASET_SCHEMA) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    enum = schema["properties"]["expected_sources"]["items"]["enum"]
    if not isinstance(enum, list) or not all(isinstance(item, str) for item in enum):
        raise ValueError(f"{schema_path}: expected_sources enum must be a string array")
    return list(enum)


def _clean_string_list(value: Any, *, field: str) -> list[str]:
    if isinstance(value, str):
        raw_items = value.splitlines()
    elif isinstance(value, list):
        raw_items = value
    else:
        raise ValueError(f"{field} must be a list or newline-delimited string")
    return [str(item).strip() for item in raw_items if str(item).strip()]


def normalize_dataset_row(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("dataset row must be an object")
    normalized: dict[str, Any] = {}
    for field in ("id", "question", "expected_evidence_strength", "referenceResponse", "category"):
        value = row.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} is required")
        normalized[field] = value.strip()
    for field in ("expected_sources", "must_include", "must_not_claim"):
        normalized[field] = _clean_string_list(row.get(field, []), field=field)
    return {key: normalized[key] for key in DATASET_ROW_KEYS}


def normalize_dataset_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        try:
            item = normalize_dataset_row(row)
        except Exception as exc:
            raise ValueError(f"row {index}: {exc}") from exc
        row_id = str(item["id"])
        if row_id in seen:
            raise ValueError(f"duplicate dataset id {row_id}")
        seen.add(row_id)
        normalized.append(item)
    if not normalized:
        raise ValueError("dataset must contain at least one row")
    return normalized


def write_dataset_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps({key: row[key] for key in DATASET_ROW_KEYS}, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def validate_recruiter_dataset_file(path: Path) -> tuple[bool, list[str]]:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--schema", str(RECRUITER_DATASET_SCHEMA), "--input", str(path), "--format", "jsonl"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return True, []
    output = (result.stderr or result.stdout).strip()
    issues = [line.strip().removeprefix("- ") for line in output.splitlines() if line.strip() and line.strip() != "validation failed:"]
    return False, issues or [output or "dataset validation failed"]


def save_dataset_rows(path: Path, rows: Iterable[dict[str, Any]]) -> tuple[bool, list[str], int]:
    normalized = normalize_dataset_rows(rows)
    temp = path.with_name(f".{path.name}.tmp")
    write_dataset_jsonl(temp, normalized)
    ok, issues = validate_recruiter_dataset_file(temp)
    if not ok:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
        return False, issues, len(normalized)
    temp.replace(path)
    return True, [], len(normalized)


def score_label(score: int) -> str:
    if score not in SCORE_LABELS:
        raise ValueError(f"score must be one of {sorted(SCORE_LABELS)}")
    return SCORE_LABELS[score]


def bedrock_score_interpretation(value: float) -> dict[str, Any]:
    exact = {0.0: 0, 0.5: 1, 1.0: 2}
    rounded = round(float(value), 4)
    if rounded in exact:
        score = exact[rounded]
        return {"bedrock_score": rounded, "exact": True, "repo_score": score, "repo_label": score_label(score), "note": "Exact repo-scale mapping."}
    nearest = min(SCORE_LABELS, key=lambda item: abs((item / 2) - rounded))
    if 0 < rounded < 0.5:
        note = "Between fail and partial on the repo's 0/1/2 scale."
    elif 0.5 < rounded < 1:
        note = "Between partial and pass on the repo's 0/1/2 scale."
    else:
        note = "Outside the expected normalized Bedrock score range."
    return {"bedrock_score": rounded, "exact": False, "repo_score": nearest, "repo_label": score_label(nearest), "note": note}


def assert_explanation_coverage() -> None:
    missing: list[str] = []
    for score in SCORE_LABELS:
        if score not in SCORE_EXPLANATIONS:
            missing.append(f"score:{score}")
    for value in EXPECTED_OUTCOMES:
        if value not in OUTCOME_EXPLANATIONS:
            missing.append(f"outcome:{value}")
    for value in EVIDENCE_STRENGTHS:
        if value not in EVIDENCE_STRENGTH_EXPLANATIONS:
            missing.append(f"evidence_strength:{value}")
    for value in FAILURE_LABELS:
        if value not in FAILURE_LABEL_EXPLANATIONS:
            missing.append(f"failure_label:{value}")
    if missing:
        raise ValueError("missing explanations for " + ", ".join(missing))


def build_empty_slots(examples: Iterable[dict[str, Any]]) -> dict[tuple[str, str], LabelSlot]:
    slots: dict[tuple[str, str], LabelSlot] = {}
    for example in examples:
        example_id = str(example["id"])
        for rubric_id in RUBRIC_ORDER:
            slot = LabelSlot(example_id=example_id, rubric_id=rubric_id)
            slots[slot.key] = slot
    return slots


def slot_from_row(row: dict[str, Any]) -> LabelSlot:
    score = int(row["expected_score"])
    if row.get("expected_score_label") != score_label(score):
        raise ValueError(f"{row.get('example_id')}/{row.get('rubric_id')}: expected_score_label does not match expected_score")
    return LabelSlot(
        example_id=str(row["example_id"]),
        rubric_id=str(row["rubric_id"]),
        source_dataset=str(row.get("source_dataset", SOURCE_DATASET)),
        score=score,
        expected_outcome=row.get("expected_outcome"),
        expected_evidence_strength=row.get("expected_evidence_strength"),
        expected_failure_labels=[str(item) for item in row.get("expected_failure_labels", [])],
        human_rationale=str(row.get("human_rationale", "")),
        label_version=str(row.get("label_version", "v1")),
    )


def load_label_slots(path: Path, *, allow_empty: bool = True) -> dict[tuple[str, str], LabelSlot]:
    rows = load_jsonl(path, allow_empty=allow_empty)
    slots: dict[tuple[str, str], LabelSlot] = {}
    duplicates: list[tuple[str, str]] = []
    for row in rows:
        slot = slot_from_row(row)
        if slot.key in slots:
            duplicates.append(slot.key)
        slots[slot.key] = slot
    if duplicates:
        rendered = ", ".join(f"{example_id}/{rubric_id}" for example_id, rubric_id in duplicates[:5])
        raise ValueError(f"duplicate labels for {rendered}")
    return slots


def merge_slots(examples: list[dict[str, Any]], existing: dict[tuple[str, str], LabelSlot]) -> dict[tuple[str, str], LabelSlot]:
    slots = build_empty_slots(examples)
    unknown = sorted(set(existing) - set(slots))
    if unknown:
        rendered = ", ".join(f"{example_id}/{rubric_id}" for example_id, rubric_id in unknown[:5])
        raise ValueError(f"labels reference unknown dataset/rubric pairs: {rendered}")
    slots.update(existing)
    return slots


def row_from_slot(slot: LabelSlot) -> dict[str, Any]:
    if slot.score is None:
        raise ValueError(f"{slot.example_id}/{slot.rubric_id}: score is required")
    rationale = slot.human_rationale.strip()
    if not rationale:
        raise ValueError(f"{slot.example_id}/{slot.rubric_id}: human_rationale is required")
    if slot.rubric_id not in RUBRIC_VERSIONS:
        raise ValueError(f"{slot.example_id}/{slot.rubric_id}: unknown rubric")
    row: dict[str, Any] = {
        "schema_version": "candidate-human-label/v1",
        "example_id": slot.example_id,
        "source_dataset": slot.source_dataset,
        "rubric_id": slot.rubric_id,
        "rubric_version": RUBRIC_VERSIONS[slot.rubric_id],
        "expected_score": slot.score,
        "expected_score_label": score_label(slot.score),
        "human_rationale": rationale,
        "labeler": "human-curated-contract",
        "label_version": slot.label_version,
    }
    if slot.expected_failure_labels:
        row["expected_failure_labels"] = sorted(set(slot.expected_failure_labels), key=FAILURE_LABELS.index)
    if slot.expected_evidence_strength:
        row["expected_evidence_strength"] = slot.expected_evidence_strength
    if slot.expected_outcome:
        row["expected_outcome"] = slot.expected_outcome
    return row


def ordered_keys(examples: list[dict[str, Any]]) -> list[tuple[str, str]]:
    return [(str(example["id"]), rubric_id) for example in examples for rubric_id in RUBRIC_ORDER]


def completed_rows(examples: list[dict[str, Any]], slots: dict[tuple[str, str], LabelSlot]) -> list[dict[str, Any]]:
    return [row_from_slot(slots[key]) for key in ordered_keys(examples)]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def save_draft(path: Path, slots: dict[tuple[str, str], LabelSlot]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [slot.__dict__ for _, slot in sorted(slots.items())]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_draft_slots(path: Path) -> dict[tuple[str, str], LabelSlot]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8") or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid draft JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(payload, list):
        raise ValueError(f"{path}: draft must be a JSON array")
    slots: dict[tuple[str, str], LabelSlot] = {}
    for index, raw in enumerate(payload, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: draft item {index} must be an object")
        score_raw = raw.get("score")
        score = int(score_raw) if score_raw not in (None, "", -1) else None
        slot = LabelSlot(
            example_id=str(raw["example_id"]),
            rubric_id=str(raw["rubric_id"]),
            source_dataset=str(raw.get("source_dataset") or SOURCE_DATASET),
            score=score,
            expected_outcome=str(raw.get("expected_outcome") or "") or None,
            expected_evidence_strength=str(raw.get("expected_evidence_strength") or "") or None,
            expected_failure_labels=[str(item) for item in raw.get("expected_failure_labels", [])],
            human_rationale=str(raw.get("human_rationale") or ""),
            label_version=str(raw.get("label_version") or "v1"),
        )
        slots[slot.key] = slot
    return slots


def validate_complete_labels(dataset: Path, labels: Path) -> tuple[bool, list[str]]:
    issues: list[str] = []
    examples = load_examples(dataset)
    try:
        existing = load_label_slots(labels, allow_empty=True)
    except Exception as exc:
        return False, [str(exc)]
    expected = set(ordered_keys(examples))
    actual = set(existing)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        issues.append(f"missing {len(missing)} label(s); first missing: {missing[0][0]}/{missing[0][1]}")
    if extra:
        issues.append(f"extra {len(extra)} label(s); first extra: {extra[0][0]}/{extra[0][1]}")
    if len(existing) != len(expected):
        issues.append(f"expected {len(expected)} labels, found {len(existing)}")
    for key in sorted(actual & expected):
        slot = existing[key]
        if slot.score is None:
            issues.append(f"{key[0]}/{key[1]}: missing score")
        if not slot.human_rationale.strip():
            issues.append(f"{key[0]}/{key[1]}: missing human_rationale")
    if issues:
        return False, issues
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--schema", str(HUMAN_LABEL_SCHEMA), "--input", str(labels)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return False, [(result.stderr or result.stdout).strip()]
    return True, []


def clear_labels(labels: Path, archive_dir: Path) -> dict[str, Any]:
    rows = load_jsonl(labels, allow_empty=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = archive_dir / f"human-labels-{timestamp}.jsonl"
    archive.write_text(labels.read_text(encoding="utf-8") if labels.exists() else "", encoding="utf-8")
    labels.parent.mkdir(parents=True, exist_ok=True)
    labels.write_text("", encoding="utf-8")
    return {"archived_rows": len(rows), "archive": archive, "labels": labels}


def load_response_context(byoi_jsonl: Path | None = None, captured_jsonl: Path | None = None) -> dict[str, str]:
    context: dict[str, str] = {}
    if byoi_jsonl:
        for row in load_jsonl(byoi_jsonl, allow_empty=True):
            row_id = str(row.get("id") or row.get("example_id") or row.get("category") or "")
            responses = row.get("modelResponses") or []
            if row_id and responses and isinstance(responses[0], dict):
                context[row_id] = str(responses[0].get("response", ""))
    if captured_jsonl:
        for row in load_jsonl(captured_jsonl, allow_empty=True):
            row_id = str(row.get("id") or row.get("example_id") or row.get("row_id") or "")
            response = row.get("response") or row.get("answer") or row.get("model_response") or row.get("content")
            if row_id and response:
                context[row_id] = str(response)
    return context


class LabelWorkbenchApp:
    def __init__(self, root: Any, *, dataset: Path, labels: Path, draft: Path, byoi_jsonl: Path | None = None, captured_jsonl: Path | None = None) -> None:
        import tkinter as tk
        from tkinter import messagebox, ttk

        self.tk = tk
        self.ttk = ttk
        self.messagebox = messagebox
        self.root = root
        self.dataset_path = dataset
        self.labels_path = labels
        self.draft_path = draft
        self.examples = load_examples(dataset)
        existing = load_label_slots(labels, allow_empty=True)
        existing.update(load_draft_slots(draft))
        self.slots = merge_slots(self.examples, existing)
        self.response_context = load_response_context(byoi_jsonl, captured_jsonl)
        self.example_index = 0
        self.rubric_index = 0
        self.failure_vars: dict[str, Any] = {}
        self.score_var = tk.IntVar(value=-1)
        self.outcome_var = tk.StringVar(value="")
        self.evidence_var = tk.StringVar(value="")

        root.title("Week 5 Human Label Workbench")
        root.geometry("1180x820")
        self._build()
        self._load_current()

    @property
    def current_example(self) -> dict[str, Any]:
        return self.examples[self.example_index]

    @property
    def current_rubric(self) -> str:
        return RUBRIC_ORDER[self.rubric_index]

    @property
    def current_slot(self) -> LabelSlot:
        return self.slots[(str(self.current_example["id"]), self.current_rubric)]

    def _build(self) -> None:
        tk = self.tk
        ttk = self.ttk
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        self.progress = ttk.Label(main, font=("TkDefaultFont", 12, "bold"))
        self.progress.pack(anchor=tk.W)

        content = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        content.pack(fill=tk.BOTH, expand=True, pady=8)

        left = ttk.Frame(content, padding=8)
        right = ttk.Frame(content, padding=8)
        content.add(left, weight=3)
        content.add(right, weight=2)

        self.example_text = tk.Text(left, wrap=tk.WORD, height=22)
        self.example_text.pack(fill=tk.BOTH, expand=True)
        self.response_text = tk.Text(left, wrap=tk.WORD, height=12)
        self.response_text.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.rubric_label = ttk.Label(right, font=("TkDefaultFont", 11, "bold"), wraplength=450)
        self.rubric_label.pack(anchor=tk.W)
        self.rubric_help = ttk.Label(right, wraplength=450)
        self.rubric_help.pack(anchor=tk.W, pady=(0, 8))

        score_box = ttk.LabelFrame(right, text="Score")
        score_box.pack(fill=tk.X, pady=4)
        for score in (2, 1, 0):
            ttk.Radiobutton(score_box, text=f"{score} / {score_label(score)}", variable=self.score_var, value=score).pack(anchor=tk.W)
            ttk.Label(score_box, text=SCORE_EXPLANATIONS[score], wraplength=430).pack(anchor=tk.W, padx=22)

        ttk.Label(right, text="Expected outcome").pack(anchor=tk.W, pady=(8, 0))
        ttk.OptionMenu(right, self.outcome_var, "", *EXPECTED_OUTCOMES, command=lambda _: self._refresh_enum_help()).pack(fill=tk.X)
        self.outcome_help = ttk.Label(right, wraplength=450)
        self.outcome_help.pack(anchor=tk.W)

        ttk.Label(right, text="Expected evidence strength").pack(anchor=tk.W, pady=(8, 0))
        ttk.OptionMenu(right, self.evidence_var, "", *EVIDENCE_STRENGTHS, command=lambda _: self._refresh_enum_help()).pack(fill=tk.X)
        self.evidence_help = ttk.Label(right, wraplength=450)
        self.evidence_help.pack(anchor=tk.W)

        failure_box = ttk.LabelFrame(right, text="Failure labels")
        failure_box.pack(fill=tk.BOTH, expand=False, pady=8)
        for label in FAILURE_LABELS:
            var = tk.BooleanVar(value=False)
            self.failure_vars[label] = var
            ttk.Checkbutton(failure_box, text=label, variable=var).pack(anchor=tk.W)
            ttk.Label(failure_box, text=FAILURE_LABEL_EXPLANATIONS[label], wraplength=430).pack(anchor=tk.W, padx=22)

        ttk.Label(right, text="Human rationale").pack(anchor=tk.W)
        self.rationale_text = tk.Text(right, wrap=tk.WORD, height=6)
        self.rationale_text.pack(fill=tk.BOTH, expand=True)

        buttons = ttk.Frame(main)
        buttons.pack(fill=tk.X)
        for text, command in (
            ("Previous example", self.prev_example),
            ("Previous rubric", self.prev_rubric),
            ("Next rubric", self.next_rubric),
            ("Next example", self.next_example),
            ("Save draft", self.save_draft_action),
            ("Validate labels", self.validate_action),
            ("Export completed labels", self.export_action),
        ):
            ttk.Button(buttons, text=text, command=command).pack(side=tk.LEFT, padx=3)

    def _refresh_enum_help(self) -> None:
        self.outcome_help.configure(text=OUTCOME_EXPLANATIONS.get(self.outcome_var.get(), "Select the expected outcome for this example/rubric."))
        self.evidence_help.configure(text=EVIDENCE_STRENGTH_EXPLANATIONS.get(self.evidence_var.get(), "Select the evidence-strength label for this example/rubric."))

    def _render_example(self) -> str:
        example = self.current_example
        return "\n".join(
            [
                f"Example: {example.get('id')}",
                f"Question: {example.get('question', '')}",
                "",
                f"Reference response: {example.get('referenceResponse', '')}",
                "",
                f"Expected sources: {', '.join(example.get('expected_sources', []))}",
                f"Must include: {', '.join(example.get('must_include', []))}",
                f"Must not claim: {', '.join(example.get('must_not_claim', []))}",
                f"Dataset expected evidence strength: {example.get('expected_evidence_strength', '')}",
            ]
        )

    def _load_current(self) -> None:
        completed = sum(1 for slot in self.slots.values() if slot.score is not None and slot.human_rationale.strip())
        total = len(self.slots)
        self.progress.configure(
            text=f"Example {self.example_index + 1}/{len(self.examples)} · Rubric {self.rubric_index + 1}/{len(RUBRIC_ORDER)} · Completed {completed}/{total}"
        )
        self.example_text.delete("1.0", self.tk.END)
        self.example_text.insert("1.0", self._render_example())
        response = self.response_context.get(str(self.current_example["id"]), "No optional captured/BYOI response loaded for this row.")
        self.response_text.delete("1.0", self.tk.END)
        self.response_text.insert("1.0", f"Actual/captured response context:\n{response}")
        self.rubric_label.configure(text=f"Rubric: {self.current_rubric}")
        self.rubric_help.configure(text=RUBRIC_EXPLANATIONS[self.current_rubric])
        slot = self.current_slot
        self.score_var.set(slot.score if slot.score is not None else -1)
        self.outcome_var.set(slot.expected_outcome or "")
        self.evidence_var.set(slot.expected_evidence_strength or "")
        for label, var in self.failure_vars.items():
            var.set(label in slot.expected_failure_labels)
        self.rationale_text.delete("1.0", self.tk.END)
        self.rationale_text.insert("1.0", slot.human_rationale)
        self._refresh_enum_help()

    def _save_current_to_memory(self, *, quiet: bool = False) -> bool:
        if not hasattr(self, "rationale_text"):
            return True
        slot = self.current_slot
        score = self.score_var.get()
        slot.score = score if score in SCORE_LABELS else None
        slot.expected_outcome = self.outcome_var.get() or None
        slot.expected_evidence_strength = self.evidence_var.get() or None
        slot.expected_failure_labels = [label for label, var in self.failure_vars.items() if var.get()]
        slot.human_rationale = self.rationale_text.get("1.0", self.tk.END).strip()
        if not quiet and slot.score is not None and not slot.human_rationale:
            return self.messagebox.askyesno("Missing rationale", "This slot has a score but no rationale. Move anyway?")
        return True

    def _move(self, example_delta: int = 0, rubric_delta: int = 0) -> None:
        if not self._save_current_to_memory():
            return
        self.example_index = max(0, min(len(self.examples) - 1, self.example_index + example_delta))
        self.rubric_index = max(0, min(len(RUBRIC_ORDER) - 1, self.rubric_index + rubric_delta))
        self._load_current()

    def prev_example(self) -> None:
        self._move(example_delta=-1)

    def next_example(self) -> None:
        self._move(example_delta=1)

    def prev_rubric(self) -> None:
        self._move(rubric_delta=-1)

    def next_rubric(self) -> None:
        self._move(rubric_delta=1)

    def save_draft_action(self) -> None:
        self._save_current_to_memory(quiet=True)
        save_draft(self.draft_path, self.slots)
        self.messagebox.showinfo("Draft saved", f"Saved draft to {repo_rel(self.draft_path)}")

    def validate_action(self) -> None:
        self._save_current_to_memory(quiet=True)
        temp = DEFAULT_ARCHIVE_DIR / "validation-preview.jsonl"
        try:
            rows = completed_rows(self.examples, self.slots)
            write_jsonl(temp, rows)
            ok, issues = validate_complete_labels(self.dataset_path, temp)
        except Exception as exc:
            ok, issues = False, [str(exc)]
        if ok:
            self.messagebox.showinfo("Validation passed", "All labels are complete and schema-valid.")
        else:
            self.messagebox.showwarning("Validation failed", "\n".join(issues[:10]))

    def export_action(self) -> None:
        self._save_current_to_memory(quiet=True)
        rows: list[dict[str, Any]] = []
        try:
            rows = completed_rows(self.examples, self.slots)
            write_jsonl(self.labels_path, rows)
            ok, issues = validate_complete_labels(self.dataset_path, self.labels_path)
        except Exception as exc:
            ok, issues = False, [str(exc)]
        if ok:
            self.messagebox.showinfo("Exported", f"Exported {len(rows)} labels to {repo_rel(self.labels_path)}")
        else:
            self.messagebox.showwarning("Export blocked", "\n".join(issues[:10]))


def run_gui(args: argparse.Namespace) -> int:
    try:
        import tkinter as tk
    except ImportError as exc:
        print(
            "human label GUI failed: tkinter is not available in this Python install. "
            "A venv will not add this missing stdlib extension; install the OS package instead "
            "(Ubuntu/Debian: sudo apt-get install python3-tk), run the workbench from a Python build that includes Tkinter, "
            "or use the browser workbench: python3 scripts/human_label_web_workbench.py --host 0.0.0.0 --dataset datasets/synthetic/recruiter-evidence-qa.jsonl --labels datasets/synthetic/human-labels.jsonl",
            file=sys.stderr,
        )
        return 1
    try:
        assert_explanation_coverage()
        root = tk.Tk()
        LabelWorkbenchApp(
            root,
            dataset=args.dataset,
            labels=args.labels,
            draft=args.draft,
            byoi_jsonl=args.byoi_jsonl,
            captured_jsonl=args.captured_jsonl,
        )
        root.mainloop()
    except Exception as exc:
        if "no display name" in str(exc).lower() or "display" in str(exc).lower():
            print(
                "human label GUI failed: no display is available for Tkinter. "
                "Because this is an SSH session, use the browser workbench instead: "
                "python3 scripts/human_label_web_workbench.py --host 0.0.0.0 --dataset datasets/synthetic/recruiter-evidence-qa.jsonl --labels datasets/synthetic/human-labels.jsonl",
                file=sys.stderr,
            )
            return 1
        print(f"human label GUI failed: {exc}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "clear":
        try:
            result = clear_labels(args.labels, args.archive_dir)
        except Exception as exc:
            print(f"clear failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({"cleared": repo_rel(result["labels"]), "archived_rows": result["archived_rows"], "archive": repo_rel(result["archive"])}, sort_keys=True))
        return 0
    if args.command == "validate":
        try:
            ok, issues = validate_complete_labels(args.dataset, args.labels)
        except Exception as exc:
            print(f"human label validation failed: {exc}", file=sys.stderr)
            return 1
        if not ok:
            print("human label validation failed:", file=sys.stderr)
            for issue in issues[:20]:
                print(f"- {issue}", file=sys.stderr)
            return 1
        print(json.dumps({"valid": True, "labels": repo_rel(args.labels), "dataset": repo_rel(args.dataset)}, sort_keys=True))
        return 0
    return run_gui(args)


if __name__ == "__main__":
    raise SystemExit(main())
