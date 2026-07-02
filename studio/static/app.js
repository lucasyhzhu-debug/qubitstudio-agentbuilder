const $ = (s) => document.querySelector(s);
let sessionId = null, currentSpec = null;

async function start() {
  const r = await fetch('/api/session/new', { method: 'POST' });
  sessionId = (await r.json()).session_id;
  $('#status').textContent = 'ready';
  send('Begin the agent-architect interview.');  // seed Q0
}

// Render assistant markdown -> sanitized HTML (bold, headings, lists, code, links).
// marked does the markdown; DOMPurify strips any unsafe tags from the model output
// before it ever touches innerHTML.
function renderMarkdown(text) {
  return DOMPurify.sanitize(marked.parse(text, { breaks: true, gfm: true }));
}

function scrollLog() { $('#log').scrollTop = $('#log').scrollHeight; }

function addBubble(who, text) {
  const d = document.createElement('div');
  d.className = 'bubble ' + who;
  // User text is plain (no markdown); assistant gets rich HTML as tokens stream in.
  if (who === 'user') d.textContent = text; else d.innerHTML = renderMarkdown(text);
  $('#log').appendChild(d); scrollLog();
  return d;
}

// The assistant emits the FULL ```spec block every turn to drive the right-hand
// blueprint; that raw JSON must never show in the chat. Strip closed blocks, and also
// a not-yet-closed trailing block so the fence/JSON never flashes mid-stream.
function stripSpec(text) {
  return text
    .replace(/```(?:spec|json)[\s\S]*?```/g, '')  // closed blocks
    .replace(/```(?:spec|json)[\s\S]*$/, '')       // an unclosed trailing block (mid-stream)
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

async function send(message) {
  if (message !== 'Begin the agent-architect interview.') addBubble('user', message);
  const bubble = addBubble('assistant', '');
  const r = await fetch('/api/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = '', acc = '';
  while (true) {
    const { value, done } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true });
    let i; while ((i = buf.indexOf('\n\n')) >= 0) {
      const line = buf.slice(0, i).replace(/^data: /, ''); buf = buf.slice(i + 2);
      if (!line) continue;
      const ev = JSON.parse(line);
      if (ev.type === 'token') { acc += ev.text; bubble.innerHTML = renderMarkdown(stripSpec(acc)); scrollLog(); }
      else if (ev.type === 'error') { acc += '\n\n**[error]** ' + ev.message; bubble.innerHTML = renderMarkdown(stripSpec(acc)); }
      else if (ev.type === 'done' && ev.spec) renderBlueprint(ev.spec);
    }
  }
}

function renderBlueprint(spec) {
  const prev = currentSpec ? JSON.stringify(currentSpec) : null;
  currentSpec = spec; $('#download').disabled = false; $('#export').disabled = false;
  const p = spec.plugin || {}, comps = spec.components || [], rt = spec.runtime || {};
  const card = (title, body) => `<div class="bp-card"><h3>${title}</h3>${body}</div>`;
  const list = (arr, f) => (arr && arr.length) ? '<ul>' + arr.map(f).join('') + '</ul>' : '<i>—</i>';
  $('#blueprint').innerHTML = DOMPurify.sanitize([
    card('Identity', `<b>${p.name || '—'}</b><p>${p.description || '—'}</p>
      <small>grade: ${p.deliverable_grade || '—'}</small>`),
    card('Components', list(comps, c => `<li><code>${c.type}</code> ${c.name || c.id}</li>`)),
    card('Tools', list(comps.filter(c => c.tools), c =>
      `<li>${c.name}: ${(c.tools || []).join(', ')}</li>`)),
    card('Storage', list(rt.storage, s => `<li>${s.what} → ${s.where}</li>`)),
    card('Memory', list(rt.memory, m => `<li>${m.fact_type}: ${m.note}</li>`)),
    card('Routines', list(rt.routines, r => `<li>${r.name} (${r.schedule}): ${r.does}</li>`)),
    card('Quality bar', `<small>${JSON.stringify(spec.quality_bar || {})}</small>`),
  ].join(''));
  if (prev && prev !== JSON.stringify(spec)) {
    $('#blueprint').querySelectorAll('.bp-card').forEach(card => {
      card.classList.add('flash'); setTimeout(() => card.classList.remove('flash'), 900);
    });
  }
}

$('#composer').addEventListener('submit', (e) => {
  e.preventDefault(); const v = $('#msg').value.trim(); if (!v) return;
  $('#msg').value = ''; send(v);
});
// Enter sends; Shift+Enter inserts a newline.
$('#msg').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    $('#composer').requestSubmit();
  }
});
$('#download').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify(currentSpec, null, 2)], { type: 'application/json' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = (currentSpec?.plugin?.name || 'agent') + '-spec.json'; a.click();
});

// ── Connect-integrations wizard (Task 13) ────────────────────────────────
// After a compose `done` that pulled in integrations, render one paste-in-your-keys
// row per integration + a Test button hitting /api/keys/test. The facilitator can
// pre-seed shared workshop values by pasting into WORKSHOP_DEFAULTS from the console
// before the session starts; shipped empty so nothing leaks by default.
window.WORKSHOP_DEFAULTS = window.WORKSHOP_DEFAULTS || {};

const WIZARD_FIELDS = {
  google: [
    { key: 'GOOGLE_OAUTH_CLIENT_ID', label: 'Google OAuth client ID' },
    { key: 'GOOGLE_OAUTH_CLIENT_SECRET', label: 'Google OAuth client secret' },
  ],
  discord: [{ key: 'DISCORD_BOT_TOKEN', label: 'Discord bot token' }],
  linear: [{ key: 'LINEAR_API_KEY', label: 'Linear API key' }],
};

// Same attribute-safe escaping idiom as shelf.js's esc() — html strings here also go
// through DOMPurify.sanitize before hitting innerHTML, this just keeps quotes/brackets
// out of the raw string.
const escAttr = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function keyRowHtml(integration) {
  if (integration === 'scheduler') {
    return `<div class="keyrow" data-int="scheduler">
      <div class="kr-head"><span class="kr-name">scheduler</span></div>
      <p class="kr-note">set up later on your machine — see the chief-of-staff INSTALL guide</p>
    </div>`;
  }
  const fields = WIZARD_FIELDS[integration] || [];
  const inputs = fields.map((f) => `<label class="kr-field">${escAttr(f.label)}
      <input type="text" data-key="${escAttr(f.key)}" value="${escAttr(window.WORKSHOP_DEFAULTS[f.key] || '')}" autocomplete="off" spellcheck="false"></label>`).join('');
  // google can never smoke-test here — it needs a minted _access_token the wizard doesn't
  // have (only client id/secret). Reframe it as a Save row: persist_only, no pass/fail
  // green state, and it's excluded from `keyed` below so it never gates the install line.
  const btnLabel = integration === 'google' ? 'Save' : 'Test';
  const btnClass = integration === 'google' ? 'kr-save' : 'kr-test';
  return `<div class="keyrow" data-int="${escAttr(integration)}">
    <div class="kr-head"><span class="kr-name">${escAttr(integration)}</span><span class="kr-status"></span></div>
    ${inputs}
    <button type="button" class="${btnClass}">${btnLabel}</button>
  </div>`;
}

function installLineHtml(ev) {
  return `<pre class="install">${ev.install.split(' ; ').join('\n')}</pre>
    <p>Restart Claude Code after installing.</p>`;
}

// Wires the Test buttons + the "finish at home" reveal inside a freshly-rendered
// #buildresult. `keyed` is every integration except scheduler (scheduler has no Test
// button and never gates the install line).
function wireWizard(ev, keyed) {
  const passed = new Set();
  const unlock = () => {
    const gate = $('#wizard-gate'); if (gate) gate.hidden = false;
    const finish = $('#wizard-finish'); if (finish) finish.hidden = true;
  };
  if (!keyed.length) unlock();  // e.g. scheduler-only compose — nothing to test
  $('#buildresult').querySelectorAll('.keyrow[data-int]').forEach((row) => {
    const btn = row.querySelector('.kr-test, .kr-save');
    if (!btn) return;  // scheduler info row has no button
    const isSave = btn.classList.contains('kr-save');
    const integration = row.dataset.int;
    const idleLabel = isSave ? 'Save' : 'Test';
    btn.addEventListener('click', async () => {
      const values = {};
      row.querySelectorAll('input[data-key]').forEach((inp) => { values[inp.dataset.key] = inp.value.trim(); });
      const status = row.querySelector('.kr-status');
      btn.disabled = true; btn.textContent = isSave ? 'Saving…' : 'Testing…';
      try {
        const r = await fetch('/api/keys/test', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(isSave
            ? { integration, values, tree: ev.plugin_path, persist_only: true }
            : { integration, values, tree: ev.plugin_path }),
        });
        const out = await r.json();
        if (isSave) {
          // Save row is informational only — never the green "connected" state, and
          // never gates the install line (google is excluded from `keyed` above).
          row.classList.toggle('kr-saved', !!out.ok); row.classList.toggle('kr-fail', !out.ok);
          status.textContent = (out.ok ? 'ℹ️ ' : '❌ ') + (out.message || '');
        } else {
          row.classList.toggle('kr-pass', !!out.ok); row.classList.toggle('kr-fail', !out.ok);
          status.textContent = (out.ok ? '✅ ' : '❌ ') + (out.message || '');
          if (out.ok) { passed.add(integration); if (keyed.every((i) => passed.has(i))) unlock(); }
        }
      } catch (e) {
        row.classList.remove('kr-pass', 'kr-saved'); row.classList.add('kr-fail');
        status.textContent = '❌ ' + e.message;
      } finally {
        btn.disabled = false; btn.textContent = idleLabel;
      }
    });
  });
  const finishBtn = $('#wizard-finish');
  if (finishBtn) finishBtn.addEventListener('click', unlock);
}

const STAGES = ['preflight', 'generate', 'assemble', 'validate', 'evals', 'package'];
const STAGE_STATUS = new Set(['running', 'ok', 'fail']);
const safeStatus = (s) => (STAGE_STATUS.has(s) ? s : '');

function renderStepper(active, statusMap) {
  $('#stepper').innerHTML = STAGES.map(s =>
    `<span class="step ${safeStatus(statusMap[s])} ${s === active ? 'active' : ''}">${s}</span>`).join('');
}

// ── Post-compose voice personalization (Task 15) ─────────────────────────
// Rendered inline in the default `done` branch below, ABOVE the integrations
// wizard, only when the build that just finished was a compose (`grade ===
// "composed"`) — export builds never show it. Applying streams /api/tweak
// through the SAME streamBuild reader via a custom onDone/onError hook so it
// does NOT clobber the compose result (wizard/install line) already painted
// into #buildresult.
function personalizeFormHtml() {
  return `<div class="personalize">
    <h4>Personalize your agent's voice</h4>
    <label class="kr-field">Describe your voice
      <textarea id="tweak-voice" rows="2" placeholder="e.g. warm, terse, no corporate speak"></textarea></label>
    <label class="kr-field">Optional: paste a short writing sample
      <textarea id="tweak-sample" rows="4" placeholder="paste a short writing sample"></textarea></label>
    <button type="button" id="tweak-apply">Apply</button>
    <span id="tweak-status"></span>
  </div>`;
}

function wirePersonalize(ev) {
  const btn = $('#tweak-apply');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const ownerVoice = $('#tweak-voice').value.trim();
    const voiceSample = $('#tweak-sample').value.trim();
    const status = $('#tweak-status');
    btn.disabled = true; btn.textContent = 'Applying…'; status.textContent = '';
    try {
      await streamBuild('/api/tweak',
        { tree: ev.plugin_path, vault: ev.vault_path, fields: { OWNER_VOICE: ownerVoice, voice_sample: voiceSample } },
        {
          onDone: () => { status.textContent = '✓ applied'; },
          onError: (tev) => { status.textContent = '✗ ' + (tev.message || 'failed'); },
        });
    } finally {
      btn.disabled = false; btn.textContent = 'Apply';
    }
  });
}

// Shared SSE build-panel reader: posts `body` to `url`, streams the
// stage/component/log/done/error events, and paints #stepper/#components/
// #buildlog/#buildresult. Used by runExport (/api/export), composeAgent
// (/api/compose), and the personalize Apply button (/api/tweak) so all three
// build flows share one renderer. `opts.onDone`/`opts.onError`, when given,
// REPLACE the default done/error rendering (used by the tweak flow so it
// doesn't overwrite the compose result already on screen); omitted, both
// fall back to the original behavior.
async function streamBuild(url, body, opts = {}) {
  const statusMap = {}; const comps = {};
  renderStepper('', statusMap);
  const r = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = '';
  while (true) {
    const { value, done } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true });
    let i; while ((i = buf.indexOf('\n\n')) >= 0) {
      const line = buf.slice(0, i).replace(/^data: /, ''); buf = buf.slice(i + 2);
      if (!line) continue; const ev = JSON.parse(line);
      if (ev.type === 'stage') {
        statusMap[ev.name] = ev.status; renderStepper(ev.name, statusMap);
      } else if (ev.type === 'component') {
        comps[ev.key] = ev.status;
        $('#components').innerHTML = Object.entries(comps).map(([k, v]) =>
          `<div class="comp ${safeStatus(v)}">${DOMPurify.sanitize(k)} · ${safeStatus(v)}</div>`).join('');
      } else if (ev.type === 'log') {
        $('#buildlog').textContent += ev.text + '\n';
        $('#buildlog').scrollTop = $('#buildlog').scrollHeight;
      } else if (ev.type === 'done') {
        if (opts.onDone) { opts.onDone(ev); continue; }
        const head = `<div class="ok">✓ ${ev.grade} — <code>${ev.plugin_path}</code></div>`;
        const ints = ev.integrations || [];
        // The personalize (voice-tweak) form only makes sense for a freshly composed
        // tree — not export builds (grade "verified"/"validated") — and renders ABOVE
        // the integrations wizard / install line.
        const personalize = ev.grade === 'composed' ? personalizeFormHtml() : '';
        if (ints.length) {
          // Keyed compose: park the install line behind a wizard until every
          // integration row (except the scheduler info row and the google save-only row)
          // tests green.
          const keyed = ints.filter((i) => i !== 'scheduler' && i !== 'google');
          $('#buildresult').innerHTML = DOMPurify.sanitize(head + personalize +
            `<div class="wizard">
              <h4>Connect your integrations</h4>
              ${ints.map(keyRowHtml).join('')}
              <button type="button" id="wizard-finish" class="wizard-finish">Finish at home — show install anyway</button>
              <div id="wizard-gate" hidden>${ev.install ? installLineHtml(ev) : ''}</div>
            </div>`);
          wireWizard(ev, keyed);
        } else {
          // Local-only compose (no integrations) keeps today's immediate install line.
          $('#buildresult').innerHTML = DOMPurify.sanitize(head + personalize + (ev.install ? installLineHtml(ev) : ''));
        }
        if (ev.grade === 'composed') wirePersonalize(ev);
      } else if (ev.type === 'error') {
        if (opts.onError) { opts.onError(ev); continue; }
        const handoff = ev.handoff;
        $('#buildresult').innerHTML = DOMPurify.sanitize(
          `<div class="err">✗ ${ev.stage}: ${ev.message}</div>`);
        if (handoff) {
          const btn = document.createElement('button');
          btn.id = 'useHandoff'; btn.textContent = 'Use handoff';
          btn.onclick = () => {
            const p = document.createElement('p');
            p.innerHTML = DOMPurify.sanitize(
              `Run <code>/agent-architect</code> with <code>${handoff.spec_path}</code>`);
            $('#buildresult').appendChild(p);
          };
          $('#buildresult').appendChild(btn);
        }
      }
    }
  }
}

function resetBuildPanel() {
  $('#blueprint').hidden = true; $('#buildpanel').hidden = false;
  $('#buildlog').textContent = ''; $('#components').innerHTML = ''; $('#buildresult').innerHTML = '';
}

async function runExport() {
  if (!currentSpec) return;
  $('#export').disabled = true;
  resetBuildPanel();
  try {
    await streamBuild('/api/export', { session_id: sessionId, run_evals: $('#runevals').checked });
  } finally {
    $('#export').disabled = false;
  }
}
$('#export').addEventListener('click', runExport);

// Compose flow (skill shelf "Build my agent"): same build panel, driven by
// /api/compose instead of /api/export — no chat session/spec required.
async function composeAgent(picks, name) {
  resetBuildPanel();
  await streamBuild('/api/compose', { picks, name });
}
window.composeAgent = composeAgent;

$('#load').addEventListener('click', () => $('#loadfile').click());
$('#loadfile').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  // Reset the input so picking the SAME file again still fires `change`.
  e.target.value = '';
  if (!file) return;
  let spec;
  try { spec = JSON.parse(await file.text()); }
  catch { alert('Not valid JSON.'); return; }  // malformed file → tell the user, don't reject silently
  const r = await fetch('/api/session/load', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ spec }) });
  if (!r.ok) { alert('Invalid spec.json'); return; }
  sessionId = (await r.json()).session_id; currentSpec = null; renderBlueprint(spec);
  $('#status').textContent = 'loaded';
});

start();
