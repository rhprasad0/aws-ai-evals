#!/usr/bin/env python3
"""Browser workbench for labeling captured responses with human pass/fail labels."""

from __future__ import annotations

import argparse
import html
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from jsonschema import Draft202012Validator, FormatChecker
except Exception:  # pragma: no cover - dependency failure path
    Draft202012Validator = None  # type: ignore[assignment]
    FormatChecker = None  # type: ignore[assignment]

DEFAULT_EXAMPLES = Path("datasets/synthetic/recruiter-evidence-qa.jsonl")
DEFAULT_RESPONSES = Path("build/captured-responses/week5-all-rows.jsonl")
DEFAULT_DRAFT = Path("build/labels/human-label-draft.json")
DEFAULT_OUTPUT = Path("build/labels/human-labels.jsonl")
DEFAULT_EXAMPLE_SCHEMA = Path("schemas/eval-example.schema.json")
DEFAULT_RESPONSE_SCHEMA = Path("schemas/captured-response.schema.json")
DEFAULT_LABEL_SCHEMA = Path("schemas/human-label.schema.json")
DEFAULT_PROFILE = Path("profile.md")

@dataclass(frozen=True)
class LabelIssue:
    row: int | None
    exampleId: str | None
    field: str
    message: str

class WorkbenchError(ValueError):
    pass

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise WorkbenchError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise WorkbenchError(f"{path}:{line_number}: expected JSON object")
        records.append(value)
    return records

def dump_jsonl(records: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records)

def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)

def load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def validate_rows(rows: list[dict[str, Any]], schema_path: Path, id_field: str = "exampleId") -> list[LabelIssue]:
    issues: list[LabelIssue] = []
    seen: dict[str, int] = {}
    for index, row in enumerate(rows):
        row_id = row.get(id_field)
        if isinstance(row_id, str):
            if row_id in seen:
                issues.append(LabelIssue(index, row_id, id_field, f"Duplicate {id_field}; first seen at row {seen[row_id] + 1}"))
            else:
                seen[row_id] = index
        else:
            issues.append(LabelIssue(index, None, id_field, f"Missing string {id_field}"))
    if Draft202012Validator is None:
        return issues
    format_checker = FormatChecker() if FormatChecker is not None else None
    validator = Draft202012Validator(load_schema(schema_path), format_checker=format_checker)
    for index, row in enumerate(rows):
        row_id = row.get(id_field) if isinstance(row.get(id_field), str) else None
        for error in sorted(validator.iter_errors(row), key=lambda item: list(item.path)):
            field = ".".join(str(part) for part in error.path) or str(error.schema_path[-1])
            issues.append(LabelIssue(index, row_id, field, error.message))
    return issues

def schema_enum_options(schema: dict[str, Any], field: str) -> list[dict[str, str]]:
    spec = schema.get("properties", {}).get(field, {})
    if isinstance(spec, dict) and isinstance(spec.get("items"), dict):
        spec = spec["items"]
    options: list[dict[str, str]] = []
    for item in spec.get("oneOf", []) if isinstance(spec, dict) else []:
        if isinstance(item, dict) and "const" in item:
            options.append({"value": str(item["const"]), "description": str(item.get("description", item["const"]))})
    return options

def load_draft(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise WorkbenchError(f"Draft must be a JSON object: {path}")
    labels = value.get("labels", value)
    if not isinstance(labels, dict):
        raise WorkbenchError(f"Draft labels must be a JSON object: {path}")
    return {str(key): label for key, label in labels.items() if isinstance(label, dict)}

def normalize_draft_label(example_id: str, run_id: str, label: dict[str, Any] | None = None) -> dict[str, Any]:
    label = dict(label or {})
    return {
        "schemaVersion": "human-label/v1",
        "exampleId": example_id,
        "runId": run_id,
        "humanOutcome": label.get("humanOutcome", ""),
        "failureTags": list(label.get("failureTags", []) or []),
        "reviewNotes": str(label.get("reviewNotes", "")),
    }

def complete_label(label: dict[str, Any]) -> dict[str, Any]:
    output = {
        "schemaVersion": "human-label/v1",
        "exampleId": label["exampleId"],
        "runId": label["runId"],
        "humanOutcome": label["humanOutcome"],
    }
    if label.get("failureTags"):
        output["failureTags"] = label["failureTags"]
    if label.get("reviewNotes"):
        output["reviewNotes"] = label["reviewNotes"]
    return output

class LabelWorkbenchState:
    def __init__(
        self,
        examples_path: Path,
        responses_path: Path,
        draft_path: Path,
        output_path: Path,
        example_schema: Path,
        response_schema: Path,
        label_schema: Path,
        profile_path: Path | None = None,
    ):
        self.examples_path = examples_path
        self.responses_path = responses_path
        self.draft_path = draft_path
        self.output_path = output_path
        self.example_schema = example_schema
        self.response_schema = response_schema
        self.label_schema = label_schema
        self.profile_path = profile_path
        self.label_schema_doc = load_schema(label_schema)
        self.reload()

    def reload(self) -> None:
        self.examples = load_jsonl(self.examples_path)
        self.responses = load_jsonl(self.responses_path)
        self.draft = load_draft(self.draft_path)
        self.issues = validate_rows(self.examples, self.example_schema) + validate_rows(self.responses, self.response_schema)
        example_ids = {row["exampleId"] for row in self.examples if isinstance(row.get("exampleId"), str)}
        response_ids = {row["exampleId"] for row in self.responses if isinstance(row.get("exampleId"), str)}
        for response_id in sorted(response_ids - example_ids):
            self.issues.append(LabelIssue(None, response_id, "responses", "Captured response has no matching dataset row"))
        for example_id in sorted(example_ids - response_ids):
            self.issues.append(LabelIssue(None, example_id, "responses", "Dataset row has no captured response"))

    def profile_text(self) -> str | None:
        if not self.profile_path or not self.profile_path.exists():
            return None
        return self.profile_path.read_text(encoding="utf-8")

    def rows(self) -> list[dict[str, Any]]:
        examples_by_id = {row["exampleId"]: row for row in self.examples if isinstance(row.get("exampleId"), str)}
        rows = []
        for response in self.responses:
            example_id = response.get("exampleId")
            if not isinstance(example_id, str) or example_id not in examples_by_id:
                continue
            run_id = response.get("runId")
            if not isinstance(run_id, str):
                run_id = "unknown-run"
            label = normalize_draft_label(example_id, run_id, self.draft.get(example_id))
            rows.append({"example": examples_by_id[example_id], "response": response, "label": label})
        return rows

    def summary(self) -> dict[str, int]:
        rows = self.rows()
        pass_count = sum(1 for row in rows if row["label"].get("humanOutcome") == "pass")
        fail_count = sum(1 for row in rows if row["label"].get("humanOutcome") == "fail")
        return {
            "rows": len(rows),
            "labeled": pass_count + fail_count,
            "unlabeled": len(rows) - pass_count - fail_count,
            "pass": pass_count,
            "fail": fail_count,
            "issues": len(self.issues),
        }

    def save_draft(self, labels: dict[str, dict[str, Any]]) -> None:
        response_run_ids = {row["response"]["exampleId"]: row["response"]["runId"] for row in self.rows()}
        normalized = {
            example_id: normalize_draft_label(example_id, response_run_ids[example_id], label)
            for example_id, label in labels.items()
            if example_id in response_run_ids
        }
        atomic_write(self.draft_path, json.dumps({"savedAt": int(time.time()), "labels": normalized}, indent=2, sort_keys=True) + "\n")
        self.draft = normalized

    def export_labels(self, labels: dict[str, dict[str, Any]]) -> list[LabelIssue]:
        response_run_ids = {row["response"]["exampleId"]: row["response"]["runId"] for row in self.rows()}
        records: list[dict[str, Any]] = []
        issues: list[LabelIssue] = []
        for example_id in sorted(response_run_ids):
            label = normalize_draft_label(example_id, response_run_ids[example_id], labels.get(example_id))
            if label.get("humanOutcome") not in {"pass", "fail"}:
                issues.append(LabelIssue(None, example_id, "humanOutcome", "Choose pass or fail before export"))
                continue
            records.append(complete_label(label))
        issues.extend(validate_rows(records, self.label_schema))
        if issues:
            return issues
        atomic_write(self.output_path, dump_jsonl(records))
        self.draft = {record["exampleId"]: normalize_draft_label(record["exampleId"], record["runId"], record) for record in records}
        return []

    def api_state(self) -> dict[str, Any]:
        return {
            "paths": {
                "examples": str(self.examples_path),
                "responses": str(self.responses_path),
                "draft": str(self.draft_path),
                "output": str(self.output_path),
            },
            "rows": self.rows(),
            "summary": self.summary(),
            "issues": [asdict(issue) for issue in self.issues],
            "profileText": self.profile_text(),
            "options": {
                "humanOutcome": schema_enum_options(self.label_schema_doc, "humanOutcome"),
                "failureTags": schema_enum_options(self.label_schema_doc, "failureTags"),
            },
        }

HTML = """<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<title>Human Label Workbench</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;background:#10131a;color:#eef2ff}header{position:sticky;top:0;background:#171b26;padding:16px 24px;border-bottom:1px solid #2a3142}main{display:grid;grid-template-columns:320px 1fr;gap:16px;padding:16px}.panel,.row{background:#171b26;border:1px solid #2a3142;border-radius:12px;padding:16px}.row{margin-bottom:16px}.meta{color:#aab4cf;font-size:13px}.badge{display:inline-block;border:1px solid #3a4358;border-radius:999px;padding:2px 8px;margin-right:6px}textarea{width:100%;min-height:70px;background:#0c0f16;color:#eef2ff;border:1px solid #3a4358;border-radius:8px;padding:8px}button{background:#6173ff;color:white;border:0;border-radius:8px;padding:8px 12px;margin-right:8px;cursor:pointer}button.secondary{background:#30384a}label{display:block;margin:8px 0}.answer{white-space:pre-wrap;background:#0c0f16;padding:12px;border-radius:8px}.question{font-weight:700}.failtag{display:inline-block;margin-right:10px}.issue{color:#ffb4b4}.profile{white-space:pre-wrap;max-height:260px;overflow:auto;background:#0c0f16;padding:10px;border-radius:8px}.toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.hidden{display:none}</style>
</head>
<body>
<header><div class=\"toolbar\"><h1>Human Label Workbench</h1><button onclick=\"saveDraft()\">Save draft</button><button onclick=\"exportLabels()\">Export validated labels</button><button class=\"secondary\" onclick=\"loadState()\">Reload</button><input id=\"filter\" placeholder=\"filter rows\" oninput=\"render()\"></div><div id=\"status\" class=\"meta\"></div></header>
<main><aside class=\"panel\"><h2>Summary</h2><div id=\"summary\"></div><h2>Profile context</h2><div id=\"profile\" class=\"profile\"></div><h2>Issues</h2><div id=\"issues\"></div></aside><section id=\"rows\"></section></main>
<script>
let state=null;
const labels={};
function esc(s){return String(s??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));}
async function loadState(){const r=await fetch('/api/state');state=await r.json();for(const row of state.rows){labels[row.example.exampleId]={...row.label};}render();}
function render(){if(!state)return;const local=state.rows.map(row=>labels[row.example.exampleId]||row.label);const pass=local.filter(label=>label.humanOutcome==='pass').length;const fail=local.filter(label=>label.humanOutcome==='fail').length;const labeled=pass+fail;const unlabeled=state.rows.length-labeled;document.getElementById('status').textContent=`${labeled}/${state.rows.length} labeled · ${unlabeled} unlabeled · pass ${pass} · fail ${fail}`;document.getElementById('summary').innerHTML=`<p><span class=badge>rows ${state.rows.length}</span><span class=badge>labeled ${labeled}</span><span class=badge>unlabeled ${unlabeled}</span><span class=badge>pass ${pass}</span><span class=badge>fail ${fail}</span></p><p class=meta>Output: ${esc(state.paths.output)}<br>Draft: ${esc(state.paths.draft)}</p>`;document.getElementById('profile').textContent=state.profileText||'No profile.md loaded.';document.getElementById('issues').innerHTML=state.issues.length?state.issues.map(i=>`<p class=issue>${esc(i.exampleId||'global')} ${esc(i.field)}: ${esc(i.message)}</p>`).join(''):'<p class=meta>None</p>';const filter=document.getElementById('filter').value.toLowerCase();document.getElementById('rows').innerHTML=state.rows.filter(row=>JSON.stringify(row).toLowerCase().includes(filter)).map(rowHtml).join('');}
function rowHtml(row){const ex=row.example, resp=row.response, id=ex.exampleId, label=labels[id]||row.label;const tags=state.options.failureTags.map(opt=>`<label class=failtag><input type=checkbox onchange=\"setTag('${id}','${opt.value}',this.checked)\" ${label.failureTags?.includes(opt.value)?'checked':''}> ${esc(opt.value)}</label>`).join('');return `<article class=row><p><span class=badge>${esc(id)}</span><span class=badge>${esc(ex.requestClass)}</span><span class=badge>${esc(ex.expectedBehavior)}</span><span class=badge>prodAI ${esc(ex.productionAiProbe)}</span></p><p class=question>${esc(ex.question)}</p><p class=meta><b>Expected notes:</b> ${esc(ex.expectedAnswerNotes)}<br><b>Must avoid:</b> ${esc((ex.mustAvoid||[]).join(', '))}</p><h3>Captured response</h3><div class=answer>${esc(resp.response?.answer||'')}</div><h3>Human label</h3><label><input type=radio name=\"outcome-${id}\" onchange=\"setOutcome('${id}','pass')\" ${label.humanOutcome==='pass'?'checked':''}> Pass — acceptable under profile.md and row contract</label><label><input type=radio name=\"outcome-${id}\" onchange=\"setOutcome('${id}','fail')\" ${label.humanOutcome==='fail'?'checked':''}> Fail — violates expected behavior/source boundary/answer quality</label><details ${label.humanOutcome==='fail'?'open':''}><summary>Failure tags</summary>${tags}</details><label>Review notes<textarea onchange=\"setNotes('${id}',this.value)\">${esc(label.reviewNotes||'')}</textarea></label></article>`;}
function setOutcome(id,outcome){labels[id]={...(labels[id]||{}),humanOutcome:outcome,failureTags:outcome==='pass'?[]:(labels[id]?.failureTags||[])};render();}
function setTag(id,tag,checked){const label=labels[id]||{};const tags=new Set(label.failureTags||[]);checked?tags.add(tag):tags.delete(tag);labels[id]={...label,failureTags:[...tags]};}
function setNotes(id,notes){labels[id]={...(labels[id]||{}),reviewNotes:notes};}
async function postJson(url,payload){const r=await fetch(url,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(payload)});const j=await r.json();if(!r.ok)throw new Error((j.issues||[]).map(i=>`${i.exampleId||'global'} ${i.field}: ${i.message}`).join('\\n')||j.error||'request failed');return j;}
async function saveDraft(){try{await postJson('/api/draft',{labels});await loadState();alert('Draft saved');}catch(e){alert(e.message);}}
async function exportLabels(){try{const result=await postJson('/api/export',{labels});await loadState();alert(`Exported ${result.count} labels to ${result.output}`);}catch(e){alert(e.message);}}
loadState();
</script>
</body>
</html>
"""

class LabelHandler(BaseHTTPRequestHandler):
    state: LabelWorkbenchState

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body_json(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        if length == 0:
            return {}
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise WorkbenchError("Expected JSON object")
        return value

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            body = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/state":
            self._json(HTTPStatus.OK, self.state.api_state())
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._body_json()
            labels = payload.get("labels", {})
            if not isinstance(labels, dict):
                raise WorkbenchError("labels must be an object keyed by exampleId")
            if self.path == "/api/draft":
                self.state.save_draft(labels)
                self._json(HTTPStatus.OK, {"ok": True, "summary": self.state.summary()})
                return
            if self.path == "/api/export":
                issues = self.state.export_labels(labels)
                if issues:
                    self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "issues": [asdict(issue) for issue in issues]})
                    return
                self._json(HTTPStatus.OK, {"ok": True, "output": str(self.state.output_path), "count": len(self.state.rows())})
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover - defensive HTTP path
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

def make_handler(state: LabelWorkbenchState) -> type[LabelHandler]:
    class BoundLabelHandler(LabelHandler):
        pass
    BoundLabelHandler.state = state
    return BoundLabelHandler

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Browser workbench for human pass/fail labels")
    parser.add_argument("--examples", type=Path, default=DEFAULT_EXAMPLES)
    parser.add_argument("--responses", type=Path, default=DEFAULT_RESPONSES)
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--example-schema", type=Path, default=DEFAULT_EXAMPLE_SCHEMA)
    parser.add_argument("--response-schema", type=Path, default=DEFAULT_RESPONSE_SCHEMA)
    parser.add_argument("--label-schema", type=Path, default=DEFAULT_LABEL_SCHEMA)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--check", action="store_true", help="Validate input files and print state summary without serving")
    return parser

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    state = LabelWorkbenchState(
        args.examples,
        args.responses,
        args.draft,
        args.output,
        args.example_schema,
        args.response_schema,
        args.label_schema,
        args.profile,
    )
    if args.check:
        if state.issues:
            for issue in state.issues:
                print(f"FAIL: {issue.exampleId or 'global'} {issue.field}: {issue.message}")
            return 1
        summary = state.summary()
        print(f"OK: {summary['rows']} response row(s), {summary['labeled']} labeled, {summary['unlabeled']} unlabeled")
        return 0
    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    print(f"Serving label workbench at http://{args.host}:{args.port}/")
    print(f"Responses: {args.responses}")
    print(f"Draft: {args.draft}")
    print(f"Export: {args.output}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
