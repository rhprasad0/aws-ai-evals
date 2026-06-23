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
    return {
        "examples": examples,
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
    main { display: grid; grid-template-columns: minmax(360px, 1.1fr) minmax(420px, .9fr); gap: 16px; padding: 16px; }
    section { background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 14px; }
    h1, h2, h3 { margin: 0 0 8px; }
    textarea { width: 100%; min-height: 110px; box-sizing: border-box; border-radius: 8px; border: 1px solid #4b5563; background: #0b1220; color: #e5e7eb; padding: 10px; }
    select, button { border-radius: 7px; border: 1px solid #4b5563; padding: 8px; background: #0b1220; color: #e5e7eb; }
    button { cursor: pointer; margin: 4px 4px 4px 0; background: #2563eb; border-color: #3b82f6; }
    button.secondary { background: #374151; border-color: #4b5563; }
    .muted { color: #9ca3af; }
    .help { color: #bfdbfe; font-size: 0.92rem; margin: 3px 0 9px 24px; }
    .row { margin: 10px 0; }
    .pill { display: inline-block; padding: 2px 7px; border-radius: 999px; background: #374151; margin: 2px; }
    pre { white-space: pre-wrap; background: #0b1220; padding: 10px; border-radius: 8px; border: 1px solid #374151; max-height: 280px; overflow: auto; }
    label { display: block; margin: 4px 0; }
    .status { margin-top: 8px; white-space: pre-wrap; }
  </style>
</head>
<body>
  <header><h1>Week 5 Human Label Workbench</h1><div id="progress" class="muted">Loading…</div></header>
  <main>
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
const safe = x => String(x ?? '');
const list = items => (items || []).map(x => `<span class="pill">${safe(x)}</span>`).join(' ');
async function init() { state = await (await fetch('/state')).json(); renderControls(); render(); }
function renderControls() {
  document.getElementById('scoreControls').innerHTML = [2,1,0].map(score => `<label><input type="radio" name="score" value="${score}"> ${score} / ${state.scoreLabels[score]}</label><div class="help">${state.scoreExplanations[score]}</div>`).join('');
  document.getElementById('outcome').innerHTML = '<option value=""></option>' + state.outcomes.map(v => `<option value="${v}">${v}</option>`).join('');
  document.getElementById('evidence').innerHTML = '<option value=""></option>' + state.evidenceStrengths.map(v => `<option value="${v}">${v}</option>`).join('');
  document.getElementById('failureControls').innerHTML = state.failureLabels.map(v => `<label><input type="checkbox" value="${v}"> ${v}</label><div class="help">${state.failureLabelExplanations[v]}</div>`).join('');
  document.getElementById('outcome').onchange = () => { document.getElementById('outcomeHelp').innerText = state.outcomeExplanations[document.getElementById('outcome').value] || ''; saveCurrent(); };
  document.getElementById('evidence').onchange = () => { document.getElementById('evidenceHelp').innerText = state.evidenceStrengthExplanations[document.getElementById('evidence').value] || ''; saveCurrent(); };
  document.getElementById('rationale').oninput = saveCurrent;
  document.querySelectorAll('input[name=score]').forEach(el => el.onchange = saveCurrent);
  document.querySelectorAll('#failureControls input').forEach(el => el.onchange = saveCurrent);
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
function render() {
  const ex = state.examples[exampleIndex], rubric = state.rubricOrder[rubricIndex], slot = currentSlot();
  const completed = Object.values(state.slots).filter(s => s.score !== null && (s.human_rationale || '').trim()).length;
  document.getElementById('progress').innerText = `Example ${exampleIndex+1}/${state.examples.length} · Rubric ${rubricIndex+1}/${state.rubricOrder.length} · Completed ${completed}/${Object.keys(state.slots).length} · ${state.paths.labels}`;
  document.getElementById('exampleTitle').innerText = ex.id;
  document.getElementById('question').innerText = safe(ex.question);
  document.getElementById('reference').innerText = safe(ex.referenceResponse);
  document.getElementById('sources').innerHTML = list(ex.expected_sources);
  document.getElementById('mustInclude').innerHTML = list(ex.must_include);
  document.getElementById('mustNotClaim').innerHTML = list(ex.must_not_claim);
  document.getElementById('datasetEvidence').innerText = safe(ex.expected_evidence_strength);
  document.getElementById('responseContext').innerText = state.responseContext[ex.id] || 'No optional captured/BYOI response loaded for this row.';
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
function canMove() { saveCurrent(); const s = currentSlot(); return !(s.score !== null && !(s.human_rationale || '').trim()) || confirm('This slot has a score but no rationale. Move anyway?'); }
function moveExample(delta) { if (!canMove()) return; exampleIndex = Math.max(0, Math.min(state.examples.length - 1, exampleIndex + delta)); render(); }
function moveRubric(delta) { if (!canMove()) return; rubricIndex = Math.max(0, Math.min(state.rubricOrder.length - 1, rubricIndex + delta)); render(); }
async function post(path) { saveCurrent(); const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({slots: state.slots})}); const text = await res.text(); document.getElementById('status').innerText = text; render(); }
function saveDraft() { post('/draft'); }
function exportLabels() { post('/export'); }
init();
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
