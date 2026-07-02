# Task 0 Findings — claude -p spike (captured 2026-06-22, CLI v2.1.183)

Environment: Windows 11, repo `.venv` Python 3.14.2, `claude` resolves to
`C:\Users\Irfan\.local\bin\claude.EXE`.

## (a) `assistant` event shape
Text lives at `message.content[].text` for parts where `part.type == "text"`.
Example: `{"type":"assistant","message":{...,"content":[{"type":"text","text":"Hello there, friend!"}],...},"session_id":"..."}`.
→ Plan's `assistant_text()` full-message path is correct.

## (b) `result` event shape + session_id
`{"type":"result","subtype":"success","is_error":false,...,"result":"Hello there, friend!","session_id":"...","total_cost_usd":...}`.
`session_id` is a **top-level** field (present on assistant, result, and stream_event lines).
`type:"result"` = end of turn. → `is_turn_end()` and `session_id()` paths correct.

## (c) partial `stream_event` / token delta path
`{"type":"stream_event","event":{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello,"}},"session_id":"..."}`.
Text path: `event.event.delta.text` when `event.event.type == "content_block_delta"`.
→ Plan's `assistant_text()` partial path is correct. `--include-partial-messages` works
and yields per-token `text_delta` lines (kept in `build_argv`).

## (d) hook suppression
The user's global `SessionStart:startup` hooks flood every turn with `type:"system"`
lines (8 `hook_name` lines per turn in the plain fixture).
- **Attempt A** (`--settings '{"hooks":{}}'`): did NOT suppress — still 8 hook lines.
- **Decision (per plan rule):** neither inline-settings suppression is reliable, so the
  parser's `type:"system"` filter (Task 2 `is_system`) + tool-less spawn (`--allowed-tools ""`)
  is the sole mitigation. This is sufficient: the chat cannot act on hook output (no tools)
  and the parser drops all `type:"system"` events before they reach the browser.

## (e) resume continuity (CP2 — load-bearing) — **PASS**
`claude -p --session-id <uuid>` then `claude -p --resume <uuid>` carries context in print mode.
Codeword test: turn 1 "Remember the codeword is BANANA." → turn 2 "What is the codeword?"
returned **BANANA**. Design proceeds with `--session-id`/`--resume` (NO stream-json
multi-message fallback needed).

## (f) Python spawn form (CP1 — load-bearing) — **PASS**
`shutil.which("claude")` → `C:\Users\Irfan\.local\bin\claude.EXE` (a real `.EXE` on this box,
not a `.cmd`/`.ps1` shim). `asyncio.create_subprocess_exec(p, "-p", "hi", "--output-format",
"text", ...)` launches with no `FileNotFoundError` and no shell. **Working invocation form:**
plain argv list with the `shutil.which` result as argv[0] — no `cmd.exe /c` wrapper required.
→ Task 4 `resolve_claude()` = `shutil.which("claude")` is correct as written.

## Fixtures produced
- `stream-plain.jsonl` (12 lines: system flood → assistant → result)
- `stream-partial.jsonl` (20 lines: + stream_event content_block_delta token deltas)
