#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import human_label_workbench as labels


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Browser-based Week 5 human-label workbench.")
    parser.add_argument("--dataset", type=Path, default=labels.DEFAULT_DATASET)
    parser.add_argument("--labels", type=Path, default=labels.DEFAULT_LABELS)
    parser.add_argument("--draft", type=Path, default=labels.DEFAULT_DRAFT)
    parser.add_argument("--byoi-jsonl", type=Path)
    parser.add_argument("--captured-jsonl", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true", help="Do not try to open a browser on the server host.")
    return parser.parse_args()


def state_payload(args: argparse.Namespace) -> dict[str, Any]:
    examples = labels.load_examples(args.dataset)
    existing = labels.load_label_slots(args.labels, allow_empty=True)
    existing.update(labels.load_draft_slots(args.draft))
    slots = labels.merge_slots(examples, existing)
    source_options = labels.source_label_options()
    return {
        "examples": examples,
        "datasetRows": examples,
        "sourceLabelOptions": source_options,
        "sourceLabelExplanations": {value: "Allowed public source label from the recruiter-evidence dataset schema." for value in source_options},
        "slots": {f"{example_id}::{rubric_id}": slot.__dict__ for (example_id, rubric_id), slot in slots.items()},
        "rubricOrder": list(labels.RUBRIC_ORDER),
        "rubricVersions": labels.RUBRIC_VERSIONS,
        "rubricExplanations": labels.RUBRIC_EXPLANATIONS,
        "scoreLabels": labels.SCORE_LABELS,
        "scoreExplanations": labels.SCORE_EXPLANATIONS,
        "outcomes": list(labels.EXPECTED_OUTCOMES),
        "outcomeExplanations": labels.OUTCOME_EXPLANATIONS,
        "evidenceStrengths": list(labels.EVIDENCE_STRENGTHS),
        "evidenceStrengthExplanations": labels.EVIDENCE_STRENGTH_EXPLANATIONS,
        "failureLabels": list(labels.FAILURE_LABELS),
        "failureLabelExplanations": labels.FAILURE_LABEL_EXPLANATIONS,
        "responseContext": labels.load_response_context(args.byoi_jsonl, args.captured_jsonl),
        "paths": {"dataset": labels.repo_rel(args.dataset), "labels": labels.repo_rel(args.labels)},
    }


def slots_from_payload(payload: dict[str, Any]) -> dict[tuple[str, str], labels.LabelSlot]:
    raw_slots = payload.get("slots")
    if not isinstance(raw_slots, dict):
        raise ValueError("payload.slots must be an object")
    slots: dict[tuple[str, str], labels.LabelSlot] = {}
    for slot_key, raw in raw_slots.items():
        if not isinstance(raw, dict):
            raise ValueError(f"{slot_key}: slot must be an object")
        parts = str(slot_key).split("::", 1)
        example_id = str(raw.get("example_id") or parts[0])
        rubric_id = str(raw.get("rubric_id") or parts[1])
        score_raw = raw.get("score")
        score = int(score_raw) if score_raw not in (None, "", -1) else None
        slot = labels.LabelSlot(
            example_id=example_id,
            rubric_id=rubric_id,
            source_dataset=str(raw.get("source_dataset") or labels.SOURCE_DATASET),
            score=score,
            expected_outcome=str(raw.get("expected_outcome") or "") or None,
            expected_evidence_strength=str(raw.get("expected_evidence_strength") or "") or None,
            expected_failure_labels=[str(item) for item in raw.get("expected_failure_labels", [])],
            human_rationale=str(raw.get("human_rationale") or ""),
            label_version=str(raw.get("label_version") or "v1"),
        )
        slots[slot.key] = slot
    return slots


def dataset_rows_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_rows = payload.get("datasetRows")
    if not isinstance(raw_rows, list):
        raise ValueError("payload.datasetRows must be an array")
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"datasetRows[{index}] must be an object")
        rows.append(labels.normalize_dataset_row(raw))
    return labels.normalize_dataset_rows(rows)


def app_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Week 5 Human Label Workbench</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; background: #111827; color: #e5e7eb; }
    header { padding: 14px 18px; background: #0f172a; border-bottom: 1px solid #334155; position: sticky; top: 0; z-index: 1; }
    main { display: grid; grid-template-columns: minmax(380px, 1fr) minmax(420px, .9fr); gap: 16px; padding: 16px; }
    section { background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 14px; margin-bottom: 16px; }
    h1, h2, h3 { margin: 0 0 8px; }
    textarea, input[type=text] { width: 100%; box-sizing: border-box; border-radius: 8px; border: 1px solid #4b5563; background: #0b1220; color: #e5e7eb; padding: 10px; }
    textarea { min-height: 92px; }
    select, button { border-radius: 7px; border: 1px solid #4b5563; padding: 8px; background: #0b1220; color: #e5e7eb; }
    button { cursor: pointer; margin: 4px 4px 4px 0; background: #2563eb; border-color: #3b82f6; }
    button.secondary { background: #374151; border-color: #4b5563; }
    .muted { color: #9ca3af; }
    .help { color: #bfdbfe; font-size: 0.92rem; margin: 3px 0 9px 24px; }
    .row { margin: 10px 0; }
    .pill { display: inline-block; padding: 2px 7px; border-radius: 999px; background: #374151; margin: 2px; }
    pre { white-space: pre-wrap; background: #0b1220; padding: 10px; border-radius: 8px; border: 1px solid #374151; max-height: 220px; overflow: auto; }
    label { display: block; margin: 4px 0; }
    .status { margin-top: 8px; white-space: pre-wrap; }
    .source-grid { max-height: 190px; overflow: auto; border: 1px solid #374151; border-radius: 8px; padding: 8px; background: #0b1220; }
  </style>
</head>
<body>
  <header><h1>Week 5 Human Label Workbench</h1><div><a href="/dataset-editor" style="color:#93c5fd">Open dataset row editor</a></div><div id="progress" class="muted">Loading…</div></header>
  <main>
    <div>
      <section>
        <h2 id="exampleTitle"></h2>
        <p><strong>Question:</strong> <span id="question"></span></p>
        <h3>Reference response</h3><pre id="reference"></pre>
        <div><strong>Expected sources:</strong> <span id="sources"></span></div>
        <div><strong>Must include:</strong> <span id="mustInclude"></span></div>
        <div><strong>Must not claim:</strong> <span id="mustNotClaim"></span></div>
        <div><strong>Dataset evidence strength:</strong> <span id="datasetEvidence"></span></div>
        <h3>Actual / captured response context</h3><pre id="responseContext"></pre>
      </section>
      <section>
        <h2>Dataset row editor</h2>
        <p class="muted">Edits the recruiter-evidence prompt row that feeds Nova captures and Bedrock BYOI evals. Row IDs are read-only so labels/drafts do not get orphaned.</p>
        <div class="row"><strong>ID:</strong> <span id="datasetId"></span></div>
        <div class="row"><label>Question<textarea id="datasetQuestion"></textarea></label></div>
        <div class="row"><label>Reference response<textarea id="datasetReference"></textarea></label></div>
        <div class="row"><label>Category<input id="datasetCategory" type="text"></label></div>
        <div class="row"><label>Expected evidence strength <select id="datasetEvidenceSelect"></select></label><div id="datasetEvidenceHelp" class="help"></div></div>
        <div class="row"><strong>Expected sources</strong><div class="help">Check only public source labels that support the row. Unsupported and unsupported_private rows must have no sources.</div><div id="datasetSources" class="source-grid"></div></div>
        <div class="row"><label>Must include, one per line<textarea id="datasetMustInclude"></textarea></label></div>
        <div class="row"><label>Must not claim, one per line<textarea id="datasetMustNotClaim"></textarea></label></div>
        <button onclick="saveDataset()">Save dataset changes</button>
        <button class="secondary" onclick="reloadState()">Reload dataset from disk</button>
        <button class="secondary" onclick="validateDatasetOnly()">Validate dataset only</button>
      </section>
    </div>
    <section>
      <h2 id="rubricTitle"></h2><p id="rubricHelp" class="muted"></p>
      <div class="row"><strong>Score</strong><div id="scoreControls"></div></div>
      <div class="row"><label>Expected outcome <select id="outcome"></select></label><div id="outcomeHelp" class="help"></div></div>
      <div class="row"><label>Expected evidence strength <select id="evidence"></select></label><div id="evidenceHelp" class="help"></div></div>
      <div class="row"><strong>Failure labels</strong><div id="failureControls"></div></div>
      <div class="row"><strong>Human rationale</strong><textarea id="rationale"></textarea></div>
      <button class="secondary" onclick="moveExample(-1)">Previous example</button>
      <button class="secondary" onclick="moveRubric(-1)">Previous rubric</button>
      <button onclick="moveRubric(1)">Next rubric</button>
      <button onclick="moveExample(1)">Next example</button>
      <button onclick="saveDraft()">Save draft</button>
      <button onclick="exportLabels()">Export completed labels</button>
      <div id="status" class="status muted"></div>
    </section>
  </main>
<script>
let state, exampleIndex = 0, rubricIndex = 0;
const slotKey = () => `${state.examples[exampleIndex].id}::${state.rubricOrder[rubricIndex]}`;
const currentSlot = () => state.slots[slotKey()];
const currentRow = () => state.datasetRows[exampleIndex];
const safe = x => String(x ?? '');
const htmlSafe = x => safe(x).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const list = items => (items || []).map(x => `<span class="pill">${htmlSafe(x)}</span>`).join(' ');
const lines = value => safe(value).split('\\n').map(x => x.trim()).filter(Boolean);
async function init() { await reloadState(); }
async function reloadState() { state = await (await fetch('/state')).json(); renderControls(); render(); setStatus(`Loaded ${state.paths.dataset}`); }
function setStatus(text) { document.getElementById('status').innerText = text; }
function renderControls() {
  document.getElementById('scoreControls').innerHTML = [2,1,0].map(score => `<label><input type="radio" name="score" value="${score}"> ${score} / ${state.scoreLabels[score]}</label><div class="help">${state.scoreExplanations[score]}</div>`).join('');
  document.getElementById('outcome').innerHTML = '<option value=""></option>' + state.outcomes.map(v => `<option value="${v}">${v}</option>`).join('');
  document.getElementById('evidence').innerHTML = '<option value=""></option>' + state.evidenceStrengths.map(v => `<option value="${v}">${v}</option>`).join('');
  document.getElementById('datasetEvidenceSelect').innerHTML = state.evidenceStrengths.map(v => `<option value="${v}">${v}</option>`).join('');
  document.getElementById('failureControls').innerHTML = state.failureLabels.map(v => `<label><input type="checkbox" value="${v}"> ${v}</label><div class="help">${state.failureLabelExplanations[v]}</div>`).join('');
  document.getElementById('datasetSources').innerHTML = state.sourceLabelOptions.map(v => `<label><input type="checkbox" value="${htmlSafe(v)}"> ${htmlSafe(v)}</label><div class="help">${state.sourceLabelExplanations[v]}</div>`).join('');
  document.getElementById('outcome').onchange = () => { document.getElementById('outcomeHelp').innerText = state.outcomeExplanations[document.getElementById('outcome').value] || ''; saveCurrent(); };
  document.getElementById('evidence').onchange = () => { document.getElementById('evidenceHelp').innerText = state.evidenceStrengthExplanations[document.getElementById('evidence').value] || ''; saveCurrent(); };
  document.getElementById('datasetEvidenceSelect').onchange = () => { document.getElementById('datasetEvidenceHelp').innerText = state.evidenceStrengthExplanations[document.getElementById('datasetEvidenceSelect').value] || ''; saveDatasetCurrent(); };
  ['rationale','datasetQuestion','datasetReference','datasetCategory','datasetMustInclude','datasetMustNotClaim'].forEach(id => document.getElementById(id).oninput = id === 'rationale' ? saveCurrent : saveDatasetCurrent);
  document.querySelectorAll('input[name=score]').forEach(el => el.onchange = saveCurrent);
  document.querySelectorAll('#failureControls input').forEach(el => el.onchange = saveCurrent);
  document.querySelectorAll('#datasetSources input').forEach(el => el.onchange = saveDatasetCurrent);
}
function saveCurrent() {
  if (!state) return;
  const slot = currentSlot();
  const checked = document.querySelector('input[name=score]:checked');
  slot.score = checked ? Number(checked.value) : null;
  slot.expected_outcome = document.getElementById('outcome').value || null;
  slot.expected_evidence_strength = document.getElementById('evidence').value || null;
  slot.expected_failure_labels = Array.from(document.querySelectorAll('#failureControls input:checked')).map(el => el.value);
  slot.human_rationale = document.getElementById('rationale').value.trim();
}
function saveDatasetCurrent() {
  if (!state) return;
  const row = currentRow();
  row.question = document.getElementById('datasetQuestion').value.trim();
  row.referenceResponse = document.getElementById('datasetReference').value.trim();
  row.category = document.getElementById('datasetCategory').value.trim();
  row.expected_evidence_strength = document.getElementById('datasetEvidenceSelect').value;
  row.expected_sources = Array.from(document.querySelectorAll('#datasetSources input:checked')).map(el => el.value);
  row.must_include = lines(document.getElementById('datasetMustInclude').value);
  row.must_not_claim = lines(document.getElementById('datasetMustNotClaim').value);
}
function renderDatasetEditor(ex) {
  document.getElementById('datasetId').innerText = safe(ex.id);
  document.getElementById('datasetQuestion').value = safe(ex.question);
  document.getElementById('datasetReference').value = safe(ex.referenceResponse);
  document.getElementById('datasetCategory').value = safe(ex.category);
  document.getElementById('datasetEvidenceSelect').value = safe(ex.expected_evidence_strength);
  document.getElementById('datasetEvidenceHelp').innerText = state.evidenceStrengthExplanations[ex.expected_evidence_strength] || '';
  document.querySelectorAll('#datasetSources input').forEach(el => el.checked = (ex.expected_sources || []).includes(el.value));
  document.getElementById('datasetMustInclude').value = (ex.must_include || []).join('\\n');
  document.getElementById('datasetMustNotClaim').value = (ex.must_not_claim || []).join('\\n');
}
function render() {
  const ex = currentRow(), rubric = state.rubricOrder[rubricIndex], slot = currentSlot();
  const completed = Object.values(state.slots).filter(s => s.score !== null && (s.human_rationale || '').trim()).length;
  document.getElementById('progress').innerText = `Example ${exampleIndex+1}/${state.examples.length} · Rubric ${rubricIndex+1}/${state.rubricOrder.length} · Completed ${completed}/${Object.keys(state.slots).length} · Labels: ${state.paths.labels} · Dataset: ${state.paths.dataset}`;
  document.getElementById('exampleTitle').innerText = ex.id;
  document.getElementById('question').innerText = safe(ex.question);
  document.getElementById('reference').innerText = safe(ex.referenceResponse);
  document.getElementById('sources').innerHTML = list(ex.expected_sources);
  document.getElementById('mustInclude').innerHTML = list(ex.must_include);
  document.getElementById('mustNotClaim').innerHTML = list(ex.must_not_claim);
  document.getElementById('datasetEvidence').innerText = safe(ex.expected_evidence_strength);
  document.getElementById('responseContext').innerText = state.responseContext[ex.id] || 'No optional captured/BYOI response loaded for this row.';
  renderDatasetEditor(ex);
  document.getElementById('rubricTitle').innerText = `Rubric: ${rubric}`;
  document.getElementById('rubricHelp').innerText = state.rubricExplanations[rubric] || '';
  document.querySelectorAll('input[name=score]').forEach(el => el.checked = slot.score === Number(el.value));
  document.getElementById('outcome').value = slot.expected_outcome || '';
  document.getElementById('evidence').value = slot.expected_evidence_strength || '';
  document.querySelectorAll('#failureControls input').forEach(el => el.checked = (slot.expected_failure_labels || []).includes(el.value));
  document.getElementById('rationale').value = slot.human_rationale || '';
  document.getElementById('outcomeHelp').innerText = state.outcomeExplanations[slot.expected_outcome] || '';
  document.getElementById('evidenceHelp').innerText = state.evidenceStrengthExplanations[slot.expected_evidence_strength] || '';
}
function canMove() { saveCurrent(); saveDatasetCurrent(); const s = currentSlot(); return !(s.score !== null && !(s.human_rationale || '').trim()) || confirm('This slot has a score but no rationale. Move anyway?'); }
function moveExample(delta) { if (!canMove()) return; exampleIndex = Math.max(0, Math.min(state.examples.length - 1, exampleIndex + delta)); render(); }
function moveRubric(delta) { if (!canMove()) return; rubricIndex = Math.max(0, Math.min(state.rubricOrder.length - 1, rubricIndex + delta)); render(); }
async function post(path) { saveCurrent(); const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({slots: state.slots})}); const text = await res.text(); setStatus(text); render(); }
async function saveDataset() { saveDatasetCurrent(); const res = await fetch('/dataset', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({datasetRows: state.datasetRows})}); const text = await res.text(); setStatus(text); if (res.ok) await reloadState(); }
async function validateDatasetOnly() { saveDatasetCurrent(); const res = await fetch('/dataset/validate', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({datasetRows: state.datasetRows})}); setStatus(await res.text()); }
function saveDraft() { post('/draft'); }
function exportLabels() { post('/export'); }
init();
</script>
</body></html>"""


def dataset_editor_html() -> str:
    return r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dataset Row Editor</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; background: #111827; color: #e5e7eb; }
    header { padding: 14px 18px; background: #0f172a; border-bottom: 1px solid #334155; position: sticky; top: 0; z-index: 1; }
    a { color: #93c5fd; }
    main { display: grid; grid-template-columns: minmax(260px, .45fr) minmax(520px, 1fr); gap: 16px; padding: 16px; }
    section { background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 14px; margin-bottom: 16px; }
    h1, h2, h3 { margin: 0 0 8px; }
    textarea, input[type=text], input[type=search] { width: 100%; box-sizing: border-box; border-radius: 8px; border: 1px solid #4b5563; background: #0b1220; color: #e5e7eb; padding: 10px; }
    textarea { min-height: 92px; }
    input[disabled] { color: #9ca3af; background: #111827; }
    select, button { border-radius: 7px; border: 1px solid #4b5563; padding: 8px; background: #0b1220; color: #e5e7eb; }
    button { cursor: pointer; margin: 4px 4px 4px 0; background: #2563eb; border-color: #3b82f6; }
    button.danger { background: #991b1b; border-color: #dc2626; }
    button.secondary { background: #374151; border-color: #4b5563; }
    .muted { color: #9ca3af; }
    .help { color: #bfdbfe; font-size: 0.92rem; margin: 3px 0 9px; }
    .row { margin: 10px 0; }
    .row-list { max-height: 72vh; overflow: auto; }
    .row-card { display: block; width: 100%; text-align: left; margin: 0 0 8px; background: #0b1220; border-color: #374151; }
    .row-card.selected { border-color: #60a5fa; background: #1e3a8a; }
    .source-grid { max-height: 220px; overflow: auto; border: 1px solid #374151; border-radius: 8px; padding: 8px; background: #0b1220; }
    .status { margin-top: 8px; white-space: pre-wrap; }
  </style>
</head>
<body>
  <header>
    <h1>Dataset Row Editor</h1>
    <div><a href="/">Back to human label workbench</a></div>
    <div id="progress" class="muted">Loading…</div>
  </header>
  <main>
    <section>
      <h2>Rows</h2>
      <p class="muted">Related app for editing recruiter-evidence dataset rows. Add/delete stay in browser memory until you save.</p>
      <input id="rowFilter" type="search" placeholder="Filter by row ID or question">
      <div class="row">
        <button onclick="addRow()">Add row</button>
        <button id="deleteButton" class="danger" onclick="deleteSelectedRow()">Delete row</button>
      </div>
      <div id="rowList" class="row-list"></div>
    </section>
    <section>
      <h2 id="editorTitle">Row</h2>
      <p class="help">Plain-English helper text is shown beside enum and source controls so humans are not choosing mystery-meat schema values.</p>
      <div class="row"><label>ID<input id="datasetIdInput" type="text"></label><div id="idHelp" class="help"></div></div>
      <div class="row"><label>Question<textarea id="datasetQuestion"></textarea></label></div>
      <div class="row"><label>Reference response<textarea id="datasetReference"></textarea></label></div>
      <div class="row"><label>Category<input id="datasetCategory" type="text"></label></div>
      <div class="row"><label>Evidence strength <select id="datasetEvidenceSelect"></select></label><div id="datasetEvidenceHelp" class="help"></div></div>
      <div class="row"><strong>Expected sources</strong><div class="help">Check only public source labels that support the row. Unsupported and unsupported_private rows must have no sources.</div><div id="datasetSources" class="source-grid"></div></div>
      <div class="row"><label>Must include, one per line<textarea id="datasetMustInclude"></textarea></label></div>
      <div class="row"><label>Must not claim, one per line<textarea id="datasetMustNotClaim"></textarea></label></div>
      <button onclick="saveDataset()">Save dataset changes</button>
      <button class="secondary" onclick="reloadState()">Reload dataset from disk</button>
      <button class="secondary" onclick="validateDatasetOnly()">Validate dataset only</button>
      <div id="status" class="status muted"></div>
    </section>
  </main>
<script>
let state, selectedRowIndex = 0, dirty = false, pendingDeleteIndex = null;
const safe = x => String(x ?? '');
const htmlSafe = x => safe(x).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const lines = value => safe(value).split('\n').map(x => x.trim()).filter(Boolean);
function setStatus(text) { document.getElementById('status').innerText = text; }
function selectedRow() { return state.datasetRows[selectedRowIndex]; }
async function reloadState() {
  state = await (await fetch('/state')).json();
  state.datasetRows.forEach(row => row._persisted = true);
  selectedRowIndex = Math.min(selectedRowIndex, state.datasetRows.length - 1);
  pendingDeleteIndex = null;
  dirty = false;
  renderControls();
  render();
  setStatus(`Loaded ${state.paths.dataset}`);
}
function renderControls() {
  document.getElementById('datasetEvidenceSelect').innerHTML = state.evidenceStrengths.map(v => `<option value="${htmlSafe(v)}">${htmlSafe(v)}</option>`).join('');
  document.getElementById('datasetSources').innerHTML = state.sourceLabelOptions.map(v => `<label><input type="checkbox" value="${htmlSafe(v)}"> ${htmlSafe(v)}</label><div class="help">${htmlSafe(state.sourceLabelExplanations[v])}</div>`).join('');
  ['datasetIdInput','datasetQuestion','datasetReference','datasetCategory','datasetMustInclude','datasetMustNotClaim'].forEach(id => document.getElementById(id).oninput = saveCurrentRow);
  document.getElementById('datasetEvidenceSelect').onchange = () => { saveCurrentRow(); document.getElementById('datasetEvidenceHelp').innerText = state.evidenceStrengthExplanations[document.getElementById('datasetEvidenceSelect').value] || ''; };
  document.querySelectorAll('#datasetSources input').forEach(el => el.onchange = saveCurrentRow);
  document.getElementById('rowFilter').oninput = renderRowList;
}
function renderRowList() {
  const filter = document.getElementById('rowFilter').value.toLowerCase();
  const rows = state.datasetRows.map((row, index) => ({row, index})).filter(item => `${item.row.id} ${item.row.question}`.toLowerCase().includes(filter));
  document.getElementById('rowList').innerHTML = rows.map(({row, index}) => `<button class="row-card ${index === selectedRowIndex ? 'selected' : ''}" onclick="selectRow(${index})"><strong>${htmlSafe(row.id)}</strong><br><span class="muted">${htmlSafe(safe(row.question).slice(0, 90))}</span></button>`).join('') || '<p class="muted">No matching rows.</p>';
}
function render() {
  const row = selectedRow();
  document.getElementById('progress').innerText = `${state.datasetRows.length} rows · Dataset: ${state.paths.dataset}${dirty ? ' · unsaved changes' : ''}`;
  document.getElementById('deleteButton').innerText = pendingDeleteIndex === selectedRowIndex ? 'Confirm delete row' : 'Delete row';
  document.getElementById('editorTitle').innerText = row ? `Editing ${row.id}` : 'No row selected';
  renderRowList();
  if (!row) return;
  const idInput = document.getElementById('datasetIdInput');
  idInput.value = safe(row.id);
  idInput.disabled = row._persisted === true;
  document.getElementById('idHelp').innerText = row._persisted ? 'Existing row IDs are read-only so labels/drafts do not get orphaned.' : 'New row ID is editable until the row is saved and reloaded.';
  document.getElementById('datasetQuestion').value = safe(row.question);
  document.getElementById('datasetReference').value = safe(row.referenceResponse);
  document.getElementById('datasetCategory').value = safe(row.category);
  document.getElementById('datasetEvidenceSelect').value = safe(row.expected_evidence_strength);
  document.getElementById('datasetEvidenceHelp').innerText = state.evidenceStrengthExplanations[row.expected_evidence_strength] || '';
  document.querySelectorAll('#datasetSources input').forEach(el => el.checked = (row.expected_sources || []).includes(el.value));
  document.getElementById('datasetMustInclude').value = (row.must_include || []).join('\n');
  document.getElementById('datasetMustNotClaim').value = (row.must_not_claim || []).join('\n');
}
function saveCurrentRow() {
  if (!state || !selectedRow()) return;
  const row = selectedRow();
  if (row._persisted !== true) row.id = document.getElementById('datasetIdInput').value.trim();
  row.question = document.getElementById('datasetQuestion').value.trim();
  row.referenceResponse = document.getElementById('datasetReference').value.trim();
  row.category = document.getElementById('datasetCategory').value.trim();
  row.expected_evidence_strength = document.getElementById('datasetEvidenceSelect').value;
  row.expected_sources = Array.from(document.querySelectorAll('#datasetSources input:checked')).map(el => el.value);
  row.must_include = lines(document.getElementById('datasetMustInclude').value);
  row.must_not_claim = lines(document.getElementById('datasetMustNotClaim').value);
  dirty = true;
  renderRowList();
}
function selectRow(index) { saveCurrentRow(); selectedRowIndex = index; pendingDeleteIndex = null; render(); }
function nextNewId() {
  const ids = new Set(state.datasetRows.map(row => row.id));
  let suffix = 1;
  let candidate = 'new_recruiter_row';
  while (ids.has(candidate)) candidate = `new_recruiter_row_${++suffix}`;
  return candidate;
}
function addRow() {
  saveCurrentRow();
  const id = nextNewId();
  state.datasetRows.push({
    id,
    question: 'New public-safe recruiter evidence question?',
    expected_sources: [],
    must_include: [],
    must_not_claim: [],
    expected_evidence_strength: 'calibration_required',
    referenceResponse: 'Draft public-safe reference response. Replace before saving final dataset rows.',
    category: 'recruiter',
    _persisted: false,
  });
  selectedRowIndex = state.datasetRows.length - 1;
  pendingDeleteIndex = null;
  dirty = true;
  render();
  setStatus('Added unsaved row. Save dataset changes to persist.');
}
function deleteSelectedRow() {
  if (state.datasetRows.length <= 1) { setStatus('Cannot delete the final row; the dataset must contain at least one row.'); return; }
  const row = selectedRow();
  if (pendingDeleteIndex !== selectedRowIndex) {
    pendingDeleteIndex = selectedRowIndex;
    render();
    setStatus(`Click Confirm delete row to delete ${row.id}. This deletes only the browser copy until you save. Labels/drafts for this row may become stale.`);
    return;
  }
  state.datasetRows.splice(selectedRowIndex, 1);
  selectedRowIndex = Math.max(0, Math.min(selectedRowIndex, state.datasetRows.length - 1));
  pendingDeleteIndex = null;
  dirty = true;
  render();
  setStatus('Deleted row in browser state. Save dataset changes to persist.');
}
async function saveDataset() {
  saveCurrentRow();
  const res = await fetch('/dataset', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({datasetRows: state.datasetRows})});
  const text = await res.text();
  setStatus(text);
  if (res.ok) await reloadState();
}
async function validateDatasetOnly() {
  saveCurrentRow();
  const res = await fetch('/dataset/validate', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({datasetRows: state.datasetRows})});
  setStatus(await res.text());
}
reloadState();
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    args: argparse.Namespace

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_body(self, body: str | bytes, *, status: int = 200, content_type: str = "text/plain; charset=utf-8") -> None:
        raw = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        try:
            if self.path == "/" or self.path.startswith("/?"):
                self.send_body(app_html(), content_type="text/html; charset=utf-8")
                return
            if self.path == "/dataset-editor" or self.path.startswith("/dataset-editor?"):
                self.send_body(dataset_editor_html(), content_type="text/html; charset=utf-8")
                return
            if self.path == "/state":
                self.send_body(json.dumps(state_payload(self.args)), content_type="application/json")
                return
            self.send_body("not found", status=404)
        except Exception as exc:
            self.send_body(f"error: {exc}", status=500)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if self.path == "/dataset" or self.path == "/dataset/validate":
                rows = dataset_rows_from_payload(payload)
                if self.path == "/dataset/validate":
                    temp = self.args.dataset.with_name(f".{self.args.dataset.name}.validate.tmp")
                    labels.write_dataset_jsonl(temp, rows)
                    ok, issues = labels.validate_recruiter_dataset_file(temp)
                    try:
                        temp.unlink()
                    except FileNotFoundError:
                        pass
                    if ok:
                        self.send_body(f"Dataset validation passed for {len(rows)} rows in {labels.repo_rel(self.args.dataset)}")
                    else:
                        self.send_body("Dataset validation failed:\n" + "\n".join(f"- {issue}" for issue in issues[:20]), status=400)
                    return
                ok, issues, count = labels.save_dataset_rows(self.args.dataset, rows)
                if ok:
                    self.send_body(f"Saved {count} dataset rows to {labels.repo_rel(self.args.dataset)}")
                else:
                    self.send_body("Dataset save blocked:\n" + "\n".join(f"- {issue}" for issue in issues[:20]), status=400)
                return
            slots = slots_from_payload(payload)
            if self.path == "/draft":
                labels.save_draft(self.args.draft, slots)
                self.send_body(f"Draft saved to {labels.repo_rel(self.args.draft)}")
                return
            if self.path == "/export":
                examples = labels.load_examples(self.args.dataset)
                merged = labels.merge_slots(examples, slots)
                rows = labels.completed_rows(examples, merged)
                labels.write_jsonl(self.args.labels, rows)
                ok, issues = labels.validate_complete_labels(self.args.dataset, self.args.labels)
                if ok:
                    self.send_body(f"Exported {len(rows)} labels to {labels.repo_rel(self.args.labels)}")
                else:
                    self.send_body("Export blocked:\n" + "\n".join(f"- {issue}" for issue in issues[:20]), status=400)
                return
            self.send_body("not found", status=404)
        except Exception as exc:
            self.send_body(f"error: {exc}", status=500)


def main() -> int:
    args = parse_args()
    labels.assert_explanation_coverage()
    Handler.args = args
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Human label web workbench running at {url}")
    print("Press Ctrl+C to stop.")
    if not args.no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped human label web workbench.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
