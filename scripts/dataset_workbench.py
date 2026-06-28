#!/usr/bin/env python3
"""Local browser workbench for reviewing and editing synthetic eval JSONL rows."""

from __future__ import annotations

import argparse
import html
import json
import os
import tempfile
import time
from collections import Counter
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - exercised when jsonschema is absent
    Draft202012Validator = None  # type: ignore[assignment]


CANONICAL_FIELD_ORDER = [
    "schemaVersion",
    "exampleId",
    "question",
    "requestClass",
    "expectedBehavior",
    "sourceSupport",
    "expectedAnswerNotes",
    "mustAvoid",
    "productionAiProbe",
]


@dataclass(frozen=True)
class ValidationIssue:
    row: int | None
    exampleId: str | None
    severity: str
    field: str
    message: str


class DatasetParseError(ValueError):
    pass


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise DatasetParseError(f"Dataset file not found: {path}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetParseError(f"Line {line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise DatasetParseError(f"Line {line_number}: expected a JSON object")
        records.append(value)
    return records


def _ordered_record(record: dict[str, Any]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for key in CANONICAL_FIELD_ORDER:
        if key in record:
            ordered[key] = record[key]
    for key in record:
        if key not in ordered:
            ordered[key] = record[key]
    return ordered


def dump_jsonl(records: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(_ordered_record(record), ensure_ascii=False, separators=(",", ":")) + "\n"
        for record in records
    )


def save_jsonl_atomic(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dump_jsonl(records)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def _load_schema(schema_path: Path | None) -> dict[str, Any] | None:
    if schema_path is None:
        return None
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def schema_options(schema: dict[str, Any] | None) -> dict[str, list[dict[str, str]]]:
    if not schema:
        return {}
    options: dict[str, list[dict[str, str]]] = {}
    for field, spec in schema.get("properties", {}).items():
        if not isinstance(spec, dict):
            continue
        values = []
        for item in spec.get("oneOf", []):
            if isinstance(item, dict) and "const" in item:
                values.append(
                    {
                        "value": str(item["const"]),
                        "description": str(item.get("description", item["const"])),
                    }
                )
        if values:
            options[field] = values
    return options


def validate_records(records: list[dict[str, Any]], schema_path: Path | None = None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    schema = _load_schema(schema_path)
    if not records:
        issues.append(ValidationIssue(None, None, "error", "dataset", "Dataset must contain at least one row"))
        return issues

    ids: dict[str, int] = {}
    for index, record in enumerate(records):
        example_id = record.get("exampleId") if isinstance(record.get("exampleId"), str) else None
        if example_id:
            if example_id in ids:
                first = ids[example_id]
                issues.append(
                    ValidationIssue(index, example_id, "error", "exampleId", f"Duplicate exampleId also appears at row {first + 1}")
                )
                issues.append(
                    ValidationIssue(first, example_id, "error", "exampleId", f"Duplicate exampleId also appears at row {index + 1}")
                )
            else:
                ids[example_id] = index
        else:
            issues.append(ValidationIssue(index, None, "error", "exampleId", "Missing or non-string exampleId"))

    if schema and Draft202012Validator is not None:
        validator = Draft202012Validator(schema)
        for index, record in enumerate(records):
            example_id = record.get("exampleId") if isinstance(record.get("exampleId"), str) else None
            for error in sorted(validator.iter_errors(record), key=lambda item: list(item.path)):
                field = ".".join(str(part) for part in error.path) or str(error.schema_path[-1])
                issues.append(ValidationIssue(index, example_id, "error", field, error.message))
    elif schema:
        issues.extend(_fallback_validate(records, schema))
    return _dedupe_issues(issues)


def _fallback_validate(records: list[dict[str, Any]], schema: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    required = set(schema.get("required", []))
    allowed = set(schema.get("properties", {}))
    options = {field: {item["value"] for item in values} for field, values in schema_options(schema).items()}
    consts = {
        field: spec["const"]
        for field, spec in schema.get("properties", {}).items()
        if isinstance(spec, dict) and "const" in spec
    }
    for index, record in enumerate(records):
        example_id = record.get("exampleId") if isinstance(record.get("exampleId"), str) else None
        for field in sorted(required - set(record)):
            issues.append(ValidationIssue(index, example_id, "error", field, "Missing required field"))
        for field in sorted(set(record) - allowed):
            issues.append(ValidationIssue(index, example_id, "error", field, "Unexpected field"))
        for field, allowed_values in options.items():
            if field in record and record[field] not in allowed_values:
                issues.append(ValidationIssue(index, example_id, "error", field, f"Value must be one of {sorted(allowed_values)}"))
        for field, const in consts.items():
            if field in record and record[field] != const:
                issues.append(ValidationIssue(index, example_id, "error", field, f"Value must be {const!r}"))
    return issues


def _dedupe_issues(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    seen: set[tuple[Any, ...]] = set()
    deduped: list[ValidationIssue] = []
    for issue in issues:
        key = (issue.row, issue.exampleId, issue.severity, issue.field, issue.message)
        if key not in seen:
            seen.add(key)
            deduped.append(issue)
    return deduped


def summarize_records(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    fields = ["requestClass", "expectedBehavior", "sourceSupport", "productionAiProbe"]
    summary: dict[str, dict[str, int]] = {}
    for field in fields:
        counts = Counter(str(record.get(field)) for record in records)
        summary[field] = dict(sorted(counts.items()))
    must_avoid_counts = Counter(str(item) for record in records for item in record.get("mustAvoid", []) if isinstance(item, str))
    summary["mustAvoid"] = dict(must_avoid_counts.most_common(20))
    return summary


def fingerprint(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {"mtimeNs": stat.st_mtime_ns, "size": stat.st_size}


class WorkbenchState:
    def __init__(self, dataset_path: Path, schema_path: Path | None = None, profile_path: Path | None = None):
        self.dataset_path = dataset_path
        self.schema_path = schema_path
        self.profile_path = profile_path
        self.schema = _load_schema(schema_path)
        self.options = schema_options(self.schema)
        self.records: list[dict[str, Any]] = []
        self.issues: list[ValidationIssue] = []
        self.dirty = False
        self.loaded_fingerprint: dict[str, int] | None = None
        self.reload()

    def reload(self) -> None:
        self.records = load_jsonl(self.dataset_path)
        self.issues = validate_records(self.records, self.schema_path)
        self.loaded_fingerprint = fingerprint(self.dataset_path)
        self.dirty = False

    def update_record(self, example_id: str, record: dict[str, Any]) -> bool:
        for index, existing in enumerate(self.records):
            if existing.get("exampleId") == example_id:
                if record.get("exampleId") != example_id:
                    raise ValueError("exampleId is read-only for existing rows")
                self.records[index] = record
                self.issues = validate_records(self.records, self.schema_path)
                self.dirty = True
                return True
        return False

    def save(self) -> None:
        self.issues = validate_records(self.records, self.schema_path)
        if self.issues:
            raise ValueError("Dataset has validation errors; fix them before saving")
        current = fingerprint(self.dataset_path)
        if self.loaded_fingerprint is not None and current != self.loaded_fingerprint:
            raise RuntimeError("Dataset changed on disk after this workbench loaded it; reload before saving")
        save_jsonl_atomic(self.dataset_path, self.records)
        self.loaded_fingerprint = fingerprint(self.dataset_path)
        self.dirty = False

    def profile_text(self) -> str | None:
        if not self.profile_path:
            return None
        try:
            return self.profile_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    def payload(self) -> dict[str, Any]:
        return {
            "records": self.records,
            "issues": [asdict(issue) for issue in self.issues],
            "summary": summarize_records(self.records),
            "options": self.options,
            "dirty": self.dirty,
            "datasetPath": str(self.dataset_path),
            "schemaPath": str(self.schema_path) if self.schema_path else None,
            "profileAvailable": self.profile_text() is not None,
        }


def app_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Synthetic Dataset Workbench</title>
<style>
:root { color-scheme: dark; font-family: Inter, system-ui, sans-serif; background: #101114; color: #f1f5f9; }
body { margin: 0; }
header { padding: 16px 20px; border-bottom: 1px solid #293241; background: #151923; }
header h1 { margin: 0 0 4px; font-size: 22px; }
header p { margin: 0; color: #a7b3c4; }
main { display: grid; grid-template-columns: 330px minmax(420px, 1fr) 360px; gap: 14px; padding: 14px; }
.panel { border: 1px solid #293241; background: #171b26; border-radius: 12px; padding: 12px; min-height: 0; }
.row-list { max-height: calc(100vh - 265px); overflow: auto; display: grid; gap: 8px; }
.row-button { text-align: left; border: 1px solid #334155; border-radius: 10px; padding: 10px; background: #111827; color: #f1f5f9; cursor: pointer; }
.row-button.active { outline: 2px solid #38bdf8; }
.row-button small { display: block; color: #93a4ba; margin-top: 4px; }
label { display: block; margin: 10px 0 4px; color: #cbd5e1; font-weight: 650; }
input, textarea, select { width: 100%; box-sizing: border-box; border: 1px solid #475569; border-radius: 8px; background: #0b1020; color: #f8fafc; padding: 9px; }
textarea { min-height: 88px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
button { border: 1px solid #475569; border-radius: 8px; background: #263244; color: #f8fafc; padding: 8px 10px; cursor: pointer; }
button.primary { background: #075985; border-color: #38bdf8; }
button.danger { background: #5f1f2a; border-color: #fb7185; }
button:disabled { opacity: .5; cursor: not-allowed; }
.controls { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
.status { white-space: pre-wrap; color: #dbeafe; min-height: 24px; }
.error { color: #fecaca; }
.helper { color: #94a3b8; font-size: 12px; margin: 3px 0 8px; }
.issue { border-left: 3px solid #fb7185; padding: 6px 8px; margin: 6px 0; background: #24141b; }
.counts { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px; }
.counts div { background: #0f172a; padding: 8px; border-radius: 8px; }
.profile { max-height: calc(100vh - 220px); overflow: auto; white-space: pre-wrap; font-size: 13px; color: #d6e1f0; }
.raw { min-height: 260px; }
@media (max-width: 1100px) { main { grid-template-columns: 1fr; } .row-list, .profile { max-height: 360px; } }
</style>
</head>
<body>
<header>
  <h1>Synthetic Dataset Workbench</h1>
  <p>Local-only editor for recruiter evidence eval JSONL. No model calls, no generated answers, no mystery-meat enums.</p>
</header>
<main>
  <section class="panel">
    <h2>Rows</h2>
    <div id="summary" class="counts"></div>
    <label for="search">Search</label>
    <input id="search" placeholder="ID, question, notes, mustAvoid..." oninput="renderRows()">
    <div class="controls">
      <div><label for="requestClassFilter">Request class</label><select id="requestClassFilter" onchange="renderRows()"></select><p id="requestClassHelp" class="helper"></p></div>
      <div><label for="expectedBehaviorFilter">Expected behavior</label><select id="expectedBehaviorFilter" onchange="renderRows()"></select><p id="expectedBehaviorHelp" class="helper"></p></div>
      <div><label for="sourceSupportFilter">Source support</label><select id="sourceSupportFilter" onchange="renderRows()"></select><p id="sourceSupportHelp" class="helper"></p></div>
      <div><label for="productionFilter">Production AI probe</label><select id="productionFilter" onchange="renderRows()"><option value="">All</option><option value="true">True — probes production AI claims</option><option value="false">False — general evidence/off-contract row</option></select></div>
    </div>
    <div class="toolbar">
      <button onclick="quickFilter('productionFilter','true')">Production probes</button>
      <button onclick="quickFilter('requestClassFilter','unsupported_or_overclaim')">Unsupported/overclaim</button>
      <button onclick="clearFilters()">Clear filters</button>
    </div>
    <div id="rows" class="row-list"></div>
  </section>
  <section class="panel">
    <h2>Selected row</h2>
    <div class="toolbar">
      <button class="primary" onclick="saveSelected()">Validate selected edit</button>
      <button class="primary" onclick="saveDataset()" id="saveButton">Save dataset changes</button>
      <button onclick="reloadDataset()">Reload dataset from disk</button>
      <button onclick="copySelected()">Copy selected row JSON</button>
    </div>
    <div id="status" class="status"></div>
    <div id="issues"></div>
    <label for="exampleId">exampleId</label><input id="exampleId" readonly><p class="helper">Existing row IDs are read-only so labels and reviews do not get orphaned.</p>
    <label for="question">question</label><textarea id="question"></textarea>
    <label for="requestClass">requestClass</label><select id="requestClass"></select><p id="requestClassEditorHelp" class="helper"></p>
    <label for="expectedBehavior">expectedBehavior</label><select id="expectedBehavior"></select><p id="expectedBehaviorEditorHelp" class="helper"></p>
    <label for="sourceSupport">sourceSupport</label><select id="sourceSupport"></select><p id="sourceSupportEditorHelp" class="helper"></p>
    <label for="expectedAnswerNotes">expectedAnswerNotes</label><textarea id="expectedAnswerNotes"></textarea>
    <label for="mustAvoid">mustAvoid, one item per line</label><textarea id="mustAvoid"></textarea>
    <label><input id="productionAiProbe" type="checkbox" style="width:auto"> productionAiProbe — true when the row probes production AI ownership/shipping/ops/readiness claims</label>
    <label for="rawJson">Raw JSON editor</label><textarea id="rawJson" class="raw" oninput="rawDirty=true"></textarea><p class="helper">Advanced escape hatch. The save path validates the full dataset before writing.</p>
  </section>
  <aside class="panel">
    <h2>Profile context</h2>
    <p class="helper">Read-only `profile.md` context. The workbench never edits this file.</p>
    <div id="profile" class="profile">No profile loaded.</div>
  </aside>
</main>
<script>
let state = null;
let selectedIndex = 0;
let rawDirty = false;
const fields = ['schemaVersion','exampleId','question','requestClass','expectedBehavior','sourceSupport','expectedAnswerNotes','mustAvoid','productionAiProbe'];

function optionLabel(field, value) {
  const found = (state?.options?.[field] || []).find(item => item.value === value);
  return found ? `${value} — ${found.description}` : value;
}
function optionHelp(field, value) {
  const found = (state?.options?.[field] || []).find(item => item.value === value);
  return found ? found.description : '';
}
async function loadState() {
  const res = await fetch('/api/records');
  state = await res.json();
  fillSelects();
  renderSummary();
  renderRows();
  renderSelected();
  renderIssues();
  updateStatus(`Loaded ${state.records.length} rows. Dirty: ${state.dirty ? 'yes' : 'no'}`);
  const profileRes = await fetch('/api/profile');
  const profile = await profileRes.json();
  document.getElementById('profile').textContent = profile.profile || 'No profile loaded.';
}
function fillSelect(id, field, includeAll=false) {
  const select = document.getElementById(id);
  const current = select.value;
  select.innerHTML = '';
  if (includeAll) select.add(new Option('All', ''));
  for (const item of state.options[field] || []) select.add(new Option(`${item.value} — ${item.description}`, item.value));
  if ([...select.options].some(o => o.value === current)) select.value = current;
}
function fillSelects() {
  fillSelect('requestClassFilter', 'requestClass', true);
  fillSelect('expectedBehaviorFilter', 'expectedBehavior', true);
  fillSelect('sourceSupportFilter', 'sourceSupport', true);
  fillSelect('requestClass', 'requestClass');
  fillSelect('expectedBehavior', 'expectedBehavior');
  fillSelect('sourceSupport', 'sourceSupport');
}
function renderSummary() {
  const el = document.getElementById('summary');
  el.innerHTML = '';
  for (const [field, counts] of Object.entries(state.summary || {})) {
    if (field === 'mustAvoid') continue;
    const div = document.createElement('div');
    div.innerHTML = `<strong>${field}</strong><br>${Object.entries(counts).map(([k,v]) => `${k}: ${v}`).join('<br>')}`;
    el.appendChild(div);
  }
}
function recordText(row) { return JSON.stringify(row).toLowerCase(); }
function filteredRows() {
  const q = document.getElementById('search').value.toLowerCase();
  const rc = document.getElementById('requestClassFilter').value;
  const eb = document.getElementById('expectedBehaviorFilter').value;
  const ss = document.getElementById('sourceSupportFilter').value;
  const prod = document.getElementById('productionFilter').value;
  document.getElementById('requestClassHelp').textContent = optionHelp('requestClass', rc);
  document.getElementById('expectedBehaviorHelp').textContent = optionHelp('expectedBehavior', eb);
  document.getElementById('sourceSupportHelp').textContent = optionHelp('sourceSupport', ss);
  return state.records.map((row, index) => ({row, index})).filter(({row}) => {
    return (!q || recordText(row).includes(q)) && (!rc || row.requestClass === rc) && (!eb || row.expectedBehavior === eb) && (!ss || row.sourceSupport === ss) && (!prod || String(row.productionAiProbe) === prod);
  });
}
function renderRows() {
  const el = document.getElementById('rows');
  el.innerHTML = '';
  const rows = filteredRows();
  for (const {row, index} of rows) {
    const button = document.createElement('button');
    button.className = 'row-button' + (index === selectedIndex ? ' active' : '');
    button.innerHTML = `<strong>${escapeHtml(row.exampleId || '(missing id)')}</strong><small>${escapeHtml(row.question || '')}</small>`;
    button.onclick = () => { selectedIndex = index; rawDirty = false; renderRows(); renderSelected(); renderIssues(); };
    el.appendChild(button);
  }
  if (!rows.length) el.textContent = 'No rows match the current filters.';
}
function selectedRow() { return state.records[selectedIndex] || state.records[0]; }
function renderSelected() {
  const row = selectedRow();
  if (!row) return;
  document.getElementById('exampleId').value = row.exampleId || '';
  document.getElementById('question').value = row.question || '';
  document.getElementById('requestClass').value = row.requestClass || '';
  document.getElementById('expectedBehavior').value = row.expectedBehavior || '';
  document.getElementById('sourceSupport').value = row.sourceSupport || '';
  document.getElementById('expectedAnswerNotes').value = row.expectedAnswerNotes || '';
  document.getElementById('mustAvoid').value = (row.mustAvoid || []).join('\\n');
  document.getElementById('productionAiProbe').checked = Boolean(row.productionAiProbe);
  document.getElementById('rawJson').value = JSON.stringify(row, null, 2);
  document.getElementById('requestClassEditorHelp').textContent = optionHelp('requestClass', row.requestClass);
  document.getElementById('expectedBehaviorEditorHelp').textContent = optionHelp('expectedBehavior', row.expectedBehavior);
  document.getElementById('sourceSupportEditorHelp').textContent = optionHelp('sourceSupport', row.sourceSupport);
}
function formRecord() {
  const current = selectedRow();
  const row = {};
  for (const key of fields) if (current[key] !== undefined) row[key] = current[key];
  row.schemaVersion = current.schemaVersion || 'eval-example/v1';
  row.exampleId = document.getElementById('exampleId').value;
  row.question = document.getElementById('question').value;
  row.requestClass = document.getElementById('requestClass').value;
  row.expectedBehavior = document.getElementById('expectedBehavior').value;
  row.sourceSupport = document.getElementById('sourceSupport').value;
  row.expectedAnswerNotes = document.getElementById('expectedAnswerNotes').value;
  row.mustAvoid = document.getElementById('mustAvoid').value.split('\\n').map(s => s.trim()).filter(Boolean);
  row.productionAiProbe = document.getElementById('productionAiProbe').checked;
  return row;
}
async function saveSelected() {
  let row;
  try { row = rawDirty ? JSON.parse(document.getElementById('rawJson').value) : formRecord(); }
  catch (err) { updateStatus(`Raw JSON is invalid: ${err.message}`, true); return false; }
  const id = selectedRow().exampleId;
  const res = await fetch(`/api/records/${encodeURIComponent(id)}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(row)});
  const payload = await res.json();
  if (!res.ok) { updateStatus(payload.error || 'Update failed', true); return false; }
  state = payload;
  rawDirty = false;
  renderSummary(); renderRows(); renderSelected(); renderIssues();
  updateStatus(`Validated edit for ${id}. Dirty: yes`);
  return true;
}
async function saveDataset() {
  const selectedSaved = await saveSelected();
  if (!selectedSaved) return;
  if ((state.issues || []).length) { updateStatus('Fix validation errors before saving dataset.', true); return; }
  const res = await fetch('/api/save', {method:'POST'});
  const payload = await res.json();
  if (!res.ok) { updateStatus(payload.error || 'Save failed', true); if (payload.issues) { state.issues = payload.issues; renderIssues(); } return; }
  state = payload;
  renderSummary(); renderRows(); renderSelected(); renderIssues();
  updateStatus('Saved dataset changes.');
}
async function reloadDataset() {
  const res = await fetch('/api/reload', {method:'POST'});
  state = await res.json();
  selectedIndex = 0; rawDirty = false;
  renderSummary(); renderRows(); renderSelected(); renderIssues();
  updateStatus('Reloaded dataset from disk; unsaved edits discarded.');
}
function renderIssues() {
  const el = document.getElementById('issues');
  el.innerHTML = '';
  const issues = state.issues || [];
  document.getElementById('saveButton').disabled = issues.length > 0;
  if (!issues.length) return;
  const heading = document.createElement('h3');
  heading.textContent = `${issues.length} validation issue(s)`;
  el.appendChild(heading);
  for (const issue of issues) {
    const div = document.createElement('div');
    div.className = 'issue';
    div.textContent = `Row ${issue.row === null ? 'dataset' : issue.row + 1} ${issue.exampleId || ''} ${issue.field}: ${issue.message}`;
    el.appendChild(div);
  }
}
function quickFilter(id, value) { document.getElementById(id).value = value; renderRows(); }
function clearFilters() { for (const id of ['search','requestClassFilter','expectedBehaviorFilter','sourceSupportFilter','productionFilter']) document.getElementById(id).value = ''; renderRows(); }
function copySelected() { navigator.clipboard.writeText(JSON.stringify(selectedRow(), null, 2)); updateStatus('Copied selected row JSON.'); }
function updateStatus(message, isError=false) { const el = document.getElementById('status'); el.textContent = message; el.className = 'status' + (isError ? ' error' : ''); }
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
loadState();
</script>
</body>
</html>
"""


class WorkbenchHandler(BaseHTTPRequestHandler):
    state: WorkbenchState

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> Any:
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length)
        return json.loads(data.decode("utf-8")) if data else None

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_html(app_html())
        elif path == "/api/records":
            self._send_json(self.state.payload())
        elif path == "/api/profile":
            self._send_json({"profile": self.state.profile_text()})
        else:
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path.startswith("/api/records/"):
                example_id = unquote(path.removeprefix("/api/records/"))
                record = self._read_json()
                if not isinstance(record, dict):
                    self._send_json({"error": "Expected JSON object"}, HTTPStatus.BAD_REQUEST)
                    return
                updated = self.state.update_record(example_id, record)
                if not updated:
                    self._send_json({"error": f"Unknown exampleId: {example_id}"}, HTTPStatus.NOT_FOUND)
                    return
                self._send_json(self.state.payload())
            elif path == "/api/save":
                self.state.save()
                self._send_json(self.state.payload())
            elif path == "/api/reload":
                self.state.reload()
                self._send_json(self.state.payload())
            else:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except json.JSONDecodeError as exc:
            self._send_json({"error": f"Invalid JSON request: {exc.msg}"}, HTTPStatus.BAD_REQUEST)
        except ValueError as exc:
            self._send_json({"error": str(exc), "issues": [asdict(issue) for issue in self.state.issues]}, HTTPStatus.BAD_REQUEST)
        except RuntimeError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.CONFLICT)


def make_server(state: WorkbenchState, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    class Handler(WorkbenchHandler):
        pass

    Handler.state = state
    return ThreadingHTTPServer((host, port), Handler)


def run_check(dataset_path: Path, schema_path: Path | None) -> int:
    try:
        records = load_jsonl(dataset_path)
    except DatasetParseError as exc:
        print(f"ERROR: {exc}")
        return 1
    issues = validate_records(records, schema_path)
    if issues:
        for issue in issues:
            where = "dataset" if issue.row is None else f"row {issue.row + 1}"
            print(f"ERROR: {where} {issue.exampleId or ''} {issue.field}: {issue.message}")
        return 1
    print(f"OK: {len(records)} rows validated")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review/edit a synthetic eval JSONL dataset in a local browser workbench.")
    parser.add_argument("dataset", type=Path, help="Path to recruiter-evidence JSONL dataset")
    parser.add_argument("--schema", type=Path, default=None, help="Optional JSON schema for dataset rows")
    parser.add_argument("--profile", type=Path, default=None, help="Optional read-only profile.md context")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host; default 127.0.0.1")
    parser.add_argument("--port", type=int, default=8765, help="Bind port; default 8765")
    parser.add_argument("--check", action="store_true", help="Validate dataset and exit without serving UI")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.check:
        return run_check(args.dataset, args.schema)
    state = WorkbenchState(args.dataset, args.schema, args.profile)
    server = make_server(state, args.host, args.port)
    print(f"Serving synthetic dataset workbench at http://{args.host}:{args.port}/")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
