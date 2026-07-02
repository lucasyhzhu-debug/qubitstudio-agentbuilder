"""Render an agent-architect architecture spec into a self-contained static HTML "setup review".

Pure Python standard library only — no pip dependencies (no jinja, no yaml). The output HTML
inlines all CSS and JavaScript; it has no external/CDN references and runs from a file:// URL with
no server. This matches the Windows / headless reality of this project.

CLI
---
    python -m scripts.render_setup <spec.json> --out <review.html>
        [--receipts <r.json>] [--validation <v.json>] [--benchmark <b.json>]
        [--stage proposal|postgen]

Run with cwd = the owning skill dir (``skills/agent-architect``) so it resolves as a package module.

Stages
------
``proposal`` (default): renders the *planned* setup, before any generation. This is the M1 path.
``postgen``: additionally folds in, if provided:
    --receipts   {component_id: receipt} or [receipt,...]  (file paths actually written)
    --validation {component_id: {passed: bool, message: str}} or list form (per-component pass/fail)
    --benchmark  {component_id|"overall": {pass_rate: float, ...}}  (eval pass-rates)
The receipt / validation / benchmark inputs are produced by later milestones; the code path exists
now so the same page can re-render the built tree.

Feedback loop (no server)
-------------------------
The page renders an **Approve / Request changes** form. Because there is no server to POST to, the
embedded JavaScript serializes the user's decision to a ``setup-feedback.json`` document of shape::

    {"decision": "approve"|"changes",
     "notes": "...",
     "per_component": {"<component-id>": {"action": "keep"|"change", "notes": "..."}}}

and offers it three robust, headless-friendly ways:
  1. A **Download** button that saves it as ``setup-feedback.json`` via a Blob (works offline).
  2. A read-only **copyable textarea** that always shows the current JSON (copy/paste fallback when
     downloads are blocked).
  3. A **Copy to clipboard** button.

This script prints the expected feedback path to stdout so the orchestrator skill knows exactly
where to read the decision back from (next to the generated HTML, named ``setup-feedback.json``).

Robustness
----------
Missing optional spec fields never crash — they render as "--" or sensible placeholders. The spec
is minimally validated; on a malformed spec the script prints a clear message to stderr and exits
non-zero.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path


# --------------------------------------------------------------------------- #
# Loading & validation
# --------------------------------------------------------------------------- #

class SpecError(Exception):
    """Raised when the spec is malformed enough that we should not render."""


def _load_json(path: Path, what: str):
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SpecError(f"{what} not found: {path}")
    except OSError as exc:
        raise SpecError(f"Could not read {what} ({path}): {exc}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SpecError(f"{what} is not valid JSON ({path}): {exc}")


def _load_optional_json(path_str, what: str):
    if not path_str:
        return None
    return _load_json(Path(path_str), what)


def validate_spec(spec) -> None:
    """Minimal validation: enough to render safely. Raises SpecError if malformed."""
    if not isinstance(spec, dict):
        raise SpecError("Top-level spec must be a JSON object.")
    plugin = spec.get("plugin")
    if not isinstance(plugin, dict):
        raise SpecError("Spec is missing a 'plugin' object.")
    if not plugin.get("name"):
        raise SpecError("Spec 'plugin' is missing required field 'name'.")
    components = spec.get("components", [])
    if not isinstance(components, list):
        raise SpecError("Spec 'components' must be a list.")
    for i, comp in enumerate(components):
        if not isinstance(comp, dict):
            raise SpecError(f"components[{i}] must be an object.")
        if not comp.get("id"):
            raise SpecError(f"components[{i}] is missing required field 'id'.")
        if not re.fullmatch(r'[\w:.\-/]+', comp["id"]):
            raise SpecError(f"components[{i}] id {comp['id']!r} contains characters unsafe in HTML attributes.")
        if not comp.get("type"):
            raise SpecError(f"components[{i}] (id={comp.get('id')!r}) is missing 'type'.")


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

DASH = "—"


def esc(value) -> str:
    """HTML-escape any value, rendering None/empty as an em-dash placeholder."""
    if value is None or value == "" or value == []:
        return DASH
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        if not value:
            return DASH
        return ", ".join(esc(v) for v in value)
    if isinstance(value, dict):
        if not value:
            return DASH
        return ", ".join(f"{esc(k)}: {esc(v)}" for k, v in value.items())
    return html.escape(str(value))


def _normalize_keyed(data):
    """Accept either {id: obj} or [obj-with-component_id] and return {id: obj}."""
    if data is None:
        return {}
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        out = {}
        for item in data:
            if isinstance(item, dict):
                key = item.get("component_id") or item.get("id")
                if key:
                    out[key] = item
        return out
    return {}


# --------------------------------------------------------------------------- #
# HTML building blocks
# --------------------------------------------------------------------------- #

CSS = """
:root{--bg:#0f1115;--panel:#171a21;--panel2:#1d212b;--line:#2a2f3a;--fg:#e7e9ee;
--muted:#9aa3b2;--accent:#6ea8fe;--ok:#5cd6a8;--warn:#f0b860;--bad:#f08080;
--skill:#6ea8fe;--agent:#c08cf0;--command:#5cd6a8;--mcp:#f0b860;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:28px 20px 80px}
h1{font-size:26px;margin:0 0 4px}
h2{font-size:18px;margin:32px 0 12px;border-bottom:1px solid var(--line);padding-bottom:6px}
a{color:var(--accent)}
.sub{color:var(--muted);margin:0 0 4px}
.badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;
font-weight:600;border:1px solid var(--line);background:var(--panel2)}
.badge.skill{color:var(--skill);border-color:var(--skill)}
.badge.agent{color:var(--agent);border-color:var(--agent)}
.badge.command{color:var(--command);border-color:var(--command)}
.badge.mcp{color:var(--mcp);border-color:var(--mcp)}
.badge.grade{color:var(--accent);border-color:var(--accent)}
.header{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px 22px}
.header .desc{margin:10px 0 0;color:var(--fg)}
.meta{margin-top:12px;color:var(--muted);font-size:13px}
.meta b{color:var(--fg);font-weight:600}
.tree{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 18px;
font-family:ui-monospace,Consolas,Menlo,monospace;font-size:13px;white-space:pre;overflow:auto;
color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;
border-top:3px solid var(--line)}
.card.skill{border-top-color:var(--skill)}
.card.agent{border-top-color:var(--agent)}
.card.command{border-top-color:var(--command)}
.card.mcp{border-top-color:var(--mcp)}
.card h3{margin:0 0 2px;font-size:16px}
.card .cid{color:var(--muted);font-size:12px;font-family:ui-monospace,monospace;margin-bottom:10px}
.kv{margin:7px 0;font-size:13px}
.kv .k{color:var(--muted);display:block;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.kv .v{color:var(--fg)}
.status{margin-top:10px;padding:8px 10px;border-radius:8px;font-size:13px}
.status.ok{background:rgba(92,214,168,.12);color:var(--ok);border:1px solid rgba(92,214,168,.35)}
.status.bad{background:rgba(240,128,128,.12);color:var(--bad);border:1px solid rgba(240,128,128,.4)}
.edges li{margin:4px 0}
.edges .ek{font-family:ui-monospace,monospace;color:var(--muted)}
.qbar{display:flex;gap:18px;flex-wrap:wrap}
.qbar .stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;
padding:14px 18px;min-width:150px}
.qbar .stat .n{font-size:24px;font-weight:700}
.qbar .stat .l{color:var(--muted);font-size:12px}
.note{color:var(--muted);font-size:13px}
.form{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 20px;
position:sticky;bottom:0}
.choices{display:flex;gap:12px;margin:8px 0 14px}
.choice{flex:1;border:1px solid var(--line);border-radius:10px;padding:12px 14px;cursor:pointer;
background:var(--panel2)}
.choice.sel{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent) inset}
.choice input{margin-right:8px}
textarea,input[type=text]{width:100%;background:var(--panel2);color:var(--fg);
border:1px solid var(--line);border-radius:8px;padding:8px 10px;font:13px/1.5 inherit}
.percomp{margin:10px 0}
.percomp .row{display:flex;gap:10px;align-items:center;margin:6px 0;flex-wrap:wrap}
.percomp .row label{font-size:12px;color:var(--muted)}
.btns{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
button{background:var(--accent);color:#0b1020;border:0;border-radius:8px;padding:9px 16px;
font-weight:700;cursor:pointer;font-size:14px}
button.alt{background:var(--panel2);color:var(--fg);border:1px solid var(--line)}
#out{margin-top:14px;font-family:ui-monospace,monospace;min-height:120px}
.empty{color:var(--muted);font-style:italic}
"""


def _build_tree(spec) -> str:
    name = spec.get("plugin", {}).get("name", "plugin")
    lines = [f"{name}/", "  .claude-plugin/plugin.json"]
    by_type = {"command": [], "skill": [], "agent": [], "mcp": []}
    for comp in spec.get("components", []):
        by_type.setdefault(comp.get("type", "other"), []).append(comp)
    for comp in by_type.get("command", []):
        lines.append(f"  {comp.get('rel_path', 'commands/?.md')}")
    for comp in by_type.get("skill", []):
        rp = comp.get("rel_path", "skills/?")
        lines.append(f"  {rp}/SKILL.md")
        if comp.get("needs_scripts"):
            lines.append(f"  {rp}/scripts/")
        if comp.get("needs_references"):
            lines.append(f"  {rp}/references/")
        if comp.get("needs_assets"):
            lines.append(f"  {rp}/assets/")
    for comp in by_type.get("agent", []):
        lines.append(f"  {comp.get('rel_path', 'agents/?.md')}")
    if by_type.get("mcp"):
        lines.append("  .mcp.json")
    for ctype, comps in by_type.items():
        if ctype not in ("skill", "agent", "command", "mcp"):
            for comp in comps:
                lines.append(f"  {comp.get('rel_path', ctype + '/?')}")
    if spec.get("plugin", {}).get("deliverable_grade") == "client-ready":
        lines.append("  marketplace.json")
        lines.append("  README.md")
    return html.escape("\n".join(lines))


def _card_for_component(comp, receipts, validation, benchmark, stage) -> str:
    ctype = comp.get("type", "other")
    cid = comp.get("id", "?")
    name = comp.get("name") or comp.get("server_name") or cid
    rows = [f'<h3>{esc(name)} <span class="badge {esc(ctype)}">{esc(ctype)}</span></h3>',
            f'<div class="cid">{esc(cid)}</div>']

    def kv(label, value):
        return f'<div class="kv"><span class="k">{html.escape(label)}</span>' \
               f'<span class="v">{esc(value)}</span></div>'

    if ctype == "skill":
        rows.append(kv("purpose", comp.get("purpose")))
        rows.append(kv("trigger intent", comp.get("trigger_intent")))
        rows.append(kv("description seed", comp.get("description_seed")))
        rows.append(kv("scripts", comp.get("needs_scripts")))
        rows.append(kv("references", comp.get("needs_references")))
        evals = comp.get("evals") or {}
        plan = []
        if evals.get("trigger"):
            plan.append("trigger")
        if evals.get("behavioral"):
            plan.append("behavioral")
        rows.append(kv("eval plan", plan or None))
        rows.append(kv("depends on", comp.get("depends_on")))
    elif ctype == "agent":
        rows.append(kv("purpose", comp.get("purpose")))
        rows.append(kv("tools", comp.get("tools")))
        rows.append(kv("model", comp.get("model") or "inherit"))
        rows.append(kv("invoked by", comp.get("invoked_by")))
    elif ctype == "command":
        rows.append(kv("argument hint", comp.get("argument_hint")))
        rows.append(kv("delegates to", comp.get("delegates_to")))
    elif ctype == "mcp":
        rows.append(kv("server", comp.get("server_name")))
        rows.append(kv("transport", comp.get("transport")))
        rows.append(kv("auth (you complete)", comp.get("auth_owner") or "user"))
        disc = comp.get("discovery") or {}
        rows.append(kv("discovery", disc.get("via")))
    else:
        # Unknown type: dump the remaining fields generically rather than crashing.
        for k, v in comp.items():
            if k not in ("id", "type", "name"):
                rows.append(kv(k, v))

    if stage == "postgen":
        rec = receipts.get(cid)
        if rec:
            rows.append(kv("files written", rec.get("files_written")))
        val = validation.get(cid)
        if val is not None:
            passed = val.get("passed") if isinstance(val, dict) else bool(val)
            msg = val.get("message", "") if isinstance(val, dict) else ""
            cls = "ok" if passed else "bad"
            label = "validated" if passed else "validation failed"
            rows.append(f'<div class="status {cls}">{label}'
                        f'{(": " + esc(msg)) if msg else ""}</div>')
        bench = benchmark.get(cid)
        if isinstance(bench, dict) and "pass_rate" in bench:
            rows.append(kv("eval pass rate", f"{bench['pass_rate']:.0%}"))

    return f'<div class="card {esc(ctype)}">' + "".join(rows) + "</div>"


def _build_edges(spec) -> str:
    edges = spec.get("cross_references", [])
    if not edges:
        return '<p class="empty">No cross-references declared.</p>'
    items = []
    for e in edges:
        items.append(
            f'<li><span class="ek">{esc(e.get("from"))}</span> '
            f'&rarr;<span class="ek"> {esc(e.get("to"))}</span> '
            f'<span class="badge">{esc(e.get("kind"))}</span></li>'
        )
    return '<ul class="edges">' + "".join(items) + "</ul>"


def _build_qbar(spec) -> str:
    qb = spec.get("quality_bar") or {}
    stats = [
        ("trigger accuracy", qb.get("trigger_accuracy")),
        ("behavioral pass rate", qb.get("behavioral_pass_rate")),
        ("min runs", qb.get("min_runs")),
    ]
    cells = []
    for label, val in stats:
        if isinstance(val, float):
            shown = f"{val:.0%}"
        elif val is None:
            shown = DASH
        else:
            shown = str(val)
        cells.append(f'<div class="stat"><div class="n">{shown}</div>'
                     f'<div class="l">{html.escape(label)}</div></div>')
    return '<div class="qbar">' + "".join(cells) + "</div>"


def _build_rationale(spec) -> str:
    """The 'structure it better' rationale area. Reads optional spec hints; otherwise explains
    the decomposition implicitly from the component mix."""
    shared = spec.get("shared") or {}
    parts = []
    dc = shared.get("domain_context")
    if dc:
        parts.append(f'<p><b>Domain context (shared by every component):</b> {esc(dc)}</p>')
    counts = {}
    for comp in spec.get("components", []):
        counts[comp.get("type")] = counts.get(comp.get("type"), 0) + 1
    summary = ", ".join(f"{n} {t}{'s' if n != 1 else ''}" for t, n in counts.items()) or "nothing yet"
    parts.append(f'<p><b>Proposed decomposition:</b> {esc(summary)}. '
                 'Reasoning &mdash; orchestration/reasoning lives in the skill(s); heavy or '
                 'context-polluting steps are split into isolated subagent(s); explicit entry '
                 'points are commands; external systems are reached via MCP servers (you complete '
                 'auth). Review the per-component cards above and request changes if a boundary, '
                 'tool allowlist, or model choice should differ.</p>')
    gl = shared.get("global_glossary")
    if gl:
        parts.append(f'<p class="note"><b>Glossary:</b> {esc(gl)}</p>')
    return "".join(parts)


def _feedback_js(component_ids) -> str:
    ids_json = (json.dumps(component_ids)
                .replace("&", "\\u0026")
                .replace("<", "\\u003c")
                .replace(">", "\\u003e"))
    return """
const COMPONENT_IDS = __IDS__;
function buildFeedback(){
  const decision = (document.querySelector('input[name=decision]:checked')||{}).value || 'approve';
  const notes = document.getElementById('notes').value || '';
  const per = {};
  COMPONENT_IDS.forEach(function(id){
    const act = (document.querySelector('input[name="act-'+id+'"]:checked')||{}).value || 'keep';
    const n = (document.getElementById('cn-'+id)||{}).value || '';
    if(act !== 'keep' || n){ per[id] = {action: act, notes: n}; }
  });
  return {decision: decision, notes: notes, per_component: per};
}
function refresh(){
  const fb = buildFeedback();
  document.getElementById('out').value = JSON.stringify(fb, null, 2);
  document.querySelectorAll('.choice').forEach(function(c){
    const inp = c.querySelector('input'); if(inp) c.classList.toggle('sel', inp.checked);
  });
}
function download(){
  refresh();
  const blob = new Blob([document.getElementById('out').value],
                        {type:'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'setup-feedback.json';
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}
function copyOut(){
  refresh();
  const ta = document.getElementById('out');
  ta.select(); ta.setSelectionRange(0, 99999);
  try { document.execCommand('copy'); } catch(e){}
  if(navigator.clipboard){ navigator.clipboard.writeText(ta.value).catch(function(){}); }
}
document.addEventListener('change', refresh);
document.addEventListener('input', refresh);
document.addEventListener('DOMContentLoaded', refresh);
""".replace("__IDS__", ids_json)


def _build_form(spec, feedback_path) -> str:
    comps = spec.get("components", [])
    rows = []
    for comp in comps:
        cid = comp.get("id", "?")
        name = comp.get("name") or comp.get("server_name") or cid
        rows.append(
            f'<div class="row">'
            f'<b>{esc(name)}</b> <span class="cid">{esc(cid)}</span>'
            f'<label><input type="radio" name="act-{esc(cid)}" value="keep" checked> keep</label>'
            f'<label><input type="radio" name="act-{esc(cid)}" value="change"> change</label>'
            f'<input type="text" id="cn-{esc(cid)}" placeholder="notes for this component">'
            f'</div>'
        )
    percomp = ('<div class="percomp">' + "".join(rows) + '</div>') if rows else \
              '<p class="empty">No components to annotate.</p>'
    return f"""
<div class="form">
  <h2 style="margin-top:0;border:0">Your decision</h2>
  <div class="choices">
    <label class="choice sel"><input type="radio" name="decision" value="approve" checked>
      <b>Approve</b> &mdash; lock this structure and proceed</label>
    <label class="choice"><input type="radio" name="decision" value="changes">
      <b>Request changes</b> &mdash; revise the structure first</label>
  </div>
  <label class="note">Overall notes</label>
  <textarea id="notes" rows="2" placeholder="anything to change about the overall structure"></textarea>
  <h2 style="font-size:14px;margin:16px 0 6px;border:0">Per-component</h2>
  {percomp}
  <div class="btns">
    <button onclick="download()">Download setup-feedback.json</button>
    <button class="alt" onclick="copyOut()">Copy JSON</button>
  </div>
  <p class="note">No server is involved. Download saves <code>setup-feedback.json</code>; the
  skill expects it at: <code>{esc(str(feedback_path))}</code> (move the download there if your
  browser saves elsewhere). The JSON below always reflects your current choices:</p>
  <textarea id="out" rows="8" readonly></textarea>
</div>
"""


def render_html(spec, receipts, validation, benchmark, stage, feedback_path) -> str:
    plugin = spec.get("plugin", {})
    author = plugin.get("author") or {}
    author_str = DASH
    if isinstance(author, dict) and (author.get("name") or author.get("email")):
        author_str = f"{author.get('name', '')} <{author.get('email', '')}>".strip()
    elif isinstance(author, str):
        author_str = author

    receipts = _normalize_keyed(receipts)
    validation = _normalize_keyed(validation)
    benchmark = _normalize_keyed(benchmark)
    component_ids = [c.get("id") for c in spec.get("components", []) if c.get("id")]

    stage_label = "Post-generation review" if stage == "postgen" else "Setup proposal"

    cards = "".join(
        _card_for_component(c, receipts, validation, benchmark, stage)
        for c in spec.get("components", [])
    ) or '<p class="empty">No components defined.</p>'

    header = f"""
<div class="header">
  <span class="badge grade">{esc(plugin.get('deliverable_grade'))}</span>
  <span class="badge">{esc(stage_label)}</span>
  <h1>{esc(plugin.get('name'))}</h1>
  <p class="desc">{esc(plugin.get('description'))}</p>
  <div class="meta">
    <b>author</b> {esc(author_str)} &nbsp;&middot;&nbsp;
    <b>version</b> {esc(plugin.get('version') or '0.1.0')} &nbsp;&middot;&nbsp;
    <b>license</b> {esc(plugin.get('license'))} &nbsp;&middot;&nbsp;
    <b>category</b> {esc(plugin.get('category'))}
  </div>
</div>
"""

    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(plugin.get('name'))} &mdash; {esc(stage_label)}</title>
<style>{CSS}</style></head>
<body><div class="wrap">
{header}
<h2>Component tree</h2>
<div class="tree">{_build_tree(spec)}</div>
<h2>Components</h2>
<div class="cards">{cards}</div>
<h2>Cross-reference graph</h2>
{_build_edges(spec)}
<h2>Eval &amp; quality bar</h2>
{_build_qbar(spec)}
<h2>Structure it better &mdash; rationale</h2>
{_build_rationale(spec)}
{_build_form(spec, feedback_path)}
</div>
<script>{_feedback_js(component_ids)}</script>
</body></html>
"""
    return body


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="render_setup",
        description="Render an architecture spec into a self-contained static HTML setup review.",
    )
    parser.add_argument("spec", help="Path to the architecture spec JSON.")
    parser.add_argument("--out", required=True, help="Path to write the HTML review.")
    parser.add_argument("--receipts", help="Generator receipts JSON (postgen).")
    parser.add_argument("--validation", help="Per-component validation JSON (postgen).")
    parser.add_argument("--benchmark", help="Plugin benchmark JSON (postgen).")
    parser.add_argument("--stage", choices=["proposal", "postgen"], default="proposal")
    args = parser.parse_args(argv)

    try:
        spec = _load_json(Path(args.spec), "spec")
        validate_spec(spec)
        receipts = _load_optional_json(args.receipts, "receipts")
        validation = _load_optional_json(args.validation, "validation")
        benchmark = _load_optional_json(args.benchmark, "benchmark")
    except SpecError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out_path = Path(args.out)
    feedback_path = out_path.resolve().parent / "setup-feedback.json"

    html_doc = render_html(spec, receipts, validation, benchmark, args.stage, feedback_path)

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html_doc, encoding="utf-8")
    except OSError as exc:
        print(f"error: could not write HTML to {out_path}: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote setup review: {out_path.resolve()}")
    print(f"Stage: {args.stage}")
    print(f"Expected feedback file: {feedback_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
