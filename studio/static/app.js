const $ = (s) => document.querySelector(s);
let sessionId = null, currentSpec = null, agentLive = false;

// ?mode=architect keeps the generic plugin-design interview reachable (spec §4.1/§4.7).
const MODE = new URLSearchParams(location.search).get('mode') === 'architect' ? 'architect' : 'workshop';
const SEED = MODE === 'architect' ? 'Begin the agent-architect interview.' : 'Begin the workshop interview.';
if (MODE === 'architect') { const a = $('#advanced'); if (a) a.open = true; }

// The dossier is the workshop skin (dossier spec §1); ?ui=chat keeps the old workshop
// chat reachable on the SAME backend (same session, extractor, endpoints) — the
// in-room escape hatch until dossier parity is proven at a dress rehearsal.
const UI = (MODE === 'workshop' && new URLSearchParams(location.search).get('ui') !== 'chat')
  ? 'dossier' : 'chat';

// ── Send queue ────────────────────────────────────────────────────────────
// ALL sends — participant submit, seed, [card] answers, [studio event]s — go through
// ONE promise chain so a programmatic send can never overlap an in-flight turn
// (spec §5.4.8). `.catch(() => {})` on the chain so one failed send never wedges it.
let sendChain = Promise.resolve();
function queueSend(message) {
  sendChain = sendChain.then(() => send(message)).catch(() => {});
  return sendChain;
}
window.queueSend = queueSend;

// Bracketed messages are the machine channel — never shown as user bubbles (spec §4.2).
const HIDDEN_MSG = /^\[(card|studio event)\]/;
window.onboardingActive = false;   // Task 9 flips this; gates the agent-panel repaints

// Composer baton: while a card holds the turn the composer sleeps (dashed overlay text).
if (window.cards) {
  window.cards.onBaton((holder) => {
    $('#composer').classList.toggle('asleep', holder === 'card');
    if (holder === 'composer' && !window.onboardingActive) {
      // dossier + C3: the floating dock retires when the walk hands the baton back;
      // an ask that arrived mid-walk renders into the document now (gate-2 R6)
      document.body.classList.remove('onboarding');
      if (window.dossierActive && window.dossier.renderPendingAsk) window.dossier.renderPendingAsk();
    }
  });
}

// The architect's ask (spec §4.2): render the card in its own rail, then send the
// answer back as a [card] message (suppressed from the chat by HIDDEN_MSG).
function renderAskCard(ask) {
  if (!window.cards || document.querySelector(`.card[data-card-id="${CSS.escape(ask.id)}"]`)) return;
  window.cards.mount($('#askrail'));   // own rail — panel repaints never wipe asks (review I2)
  window.cards.show({ ...ask, producer: 'ask', kind: 'question', eyebrow: 'the architect asks' },
    (a) => {
      let receipt, reply;
      if (a.skipped) { receipt = 'skipped'; reply = `[card] ${ask.title} → skipped`; }
      else {
        const labels = a.choices.map((id) => (ask.options.find((o) => o.id === id) || {}).label).filter(Boolean);
        const parts = [...labels, ...(a.custom ? [`(custom) ${a.custom}`] : [])];
        receipt = parts.join(' + ') || '—'; reply = `[card] ${ask.title} → ${parts.join('; ')}`;
      }
      window.cards.fold(ask.id, `${receipt} ✓`);
      window.cards.baton('composer');
      queueSend(reply);
    });
}
window.renderAskCard = renderAskCard;   // onboard.js replays a walk-suppressed ask (final review I6)

function setStatus(text, live) {
  const el = $('#status');
  el.innerHTML = '<i class="dot"></i>' + text.replace(/[<>&]/g, '');
  el.classList.toggle('live', !!live);
}
window.setStatus = setStatus;

// Used by onboard.js after the reveal (Task 9): create the session, seed the walk.
// Seeding goes through queueSend so it can never overlap a later programmatic send.
// `lastSeed` tracks whichever seed actually kicked off the session ('Begin onboarding.'
// on the walk, SEED otherwise) so send() never paints it as a fake user bubble.
let lastSeed = SEED;
window.startWorkshopSession = async function (seed) {
  const r = await fetch('/api/session/new', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: MODE }),
  });
  sessionId = (await r.json()).session_id;
  if (UI === 'dossier') sessionStorage.setItem('dossier-session', sessionId);
  setStatus('ready');
  lastSeed = seed || SEED;
  return queueSend(lastSeed);  // seed the first turn
};

// Beats replay (dossier spec §4.1): dossier.js restores a stored session on reload.
window.resumeSession = function (sid) { sessionId = sid; setStatus('ready'); };

// gate-2 C1: ?ui=chat is a SAME-SESSION escape hatch, not a restart — resume the
// stored dossier session and replay its beats as plain bubbles. The stored id is
// cleared only on a definitive 404 (gate-2 I6), never on a network failure.
const SEED_MSGS = ['Begin the workshop interview.', 'Begin onboarding.'];
async function tryChatResume() {
  const sid = sessionStorage.getItem('dossier-session');
  if (!sid) return false;
  let out;
  try {
    const r = await fetch(`/api/session/${sid}/beats`);
    if (r.status === 404) { sessionStorage.removeItem('dossier-session'); return false; }
    if (!r.ok) return false;
    out = await r.json();
  } catch { return false; }
  if (!out.beats || !out.beats.length) return false;
  window.resumeSession(sid);
  out.beats.forEach((b) => {
    const u = String(b.user || '');
    if (!HIDDEN_MSG.test(u) && !SEED_MSGS.includes(u)) addBubble('user', u);
    addBubble('assistant', stripSpec(b.prose || ''));
  });
  const last = out.beats[out.beats.length - 1].studio;
  if (last) {
    if (typeof window.shelfSync === 'function') window.shelfSync(last);
    renderAgentPanel(last);
    if (last.ask && !window.onboardingActive) renderAskCard(last.ask);
  }
  return true;
}

async function start() {
  let replayed = false;
  if (UI === 'dossier') {
    await window.dossier.activate();                 // resolves once the catalog is in (R7)
    replayed = await window.dossier.tryReplay();     // reload mid-journey: document restored
  } else if (MODE === 'workshop') {
    replayed = await tryChatResume();                // gate-2 C1: same session, plainer skin
  }
  // Onboarding gate: first launch (or ?onboard=1) hands the boot to the walk — it
  // creates the session and seeds the first turn itself. In dossier mode the C3 walk
  // mounts as a floating dock above the document until D3 re-skins it (spec §7.1).
  if (MODE === 'workshop') {
    const ob = await (await fetch('/api/onboarding')).json();
    const force = new URLSearchParams(location.search).get('onboard') === '1';
    if (!ob.completed || force) {
      // gate-2 S3: a reload mid-intake must resume the walk on the SAME replayed
      // session. Task 20 (D3) provides dossier.resumeIntake; until it lands, a
      // replayed-but-incomplete boot continues on the document (the C3 overlay can't
      // re-enter mid-flight — it would mint a NEW session) — the accepted D1a–D2
      // window, closed by D3.
      if (replayed && !force && UI === 'dossier' && window.dossier.resumeIntake) {
        window.dossier.resumeIntake(ob);
        return;
      }
      if (!replayed && window.onboardWalk) {
        if (UI === 'dossier') document.body.classList.add('onboarding');
        window.onboardWalk.begin(ob);
        return;                          // the walk calls startWorkshopSession itself
      }
    }
    if (replayed) return;                // the resumed session continues; never re-seed (C1)
    if (UI === 'chat' && !window.onboardingActive) renderAgentPanel(null);
  }
  return window.startWorkshopSession(SEED);
}

// Render assistant markdown -> sanitized HTML (bold, headings, lists, code, links).
// marked does the markdown; DOMPurify strips any unsafe tags from the model output
// before it ever touches innerHTML.
function renderMarkdown(text) {
  return DOMPurify.sanitize(marked.parse(text, { breaks: true, gfm: true }));
}
window.renderMarkdown = renderMarkdown;

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
    .replace(/```(?:spec|json|studio)[\s\S]*?```/g, '')  // closed blocks
    .replace(/```(?:spec|json|studio)[\s\S]*$/, '')       // an unclosed trailing block (mid-stream)
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}
window.stripSpec = stripSpec;

async function send(message) {
  const inDossier = UI === 'dossier';
  if (!inDossier && message !== lastSeed && !HIDDEN_MSG.test(message)) addBubble('user', message);
  const bubble = inDossier ? null : addBubble('assistant', '');
  let acc = '';
  try {
    const r = await fetch('/api/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
    const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = '';
    while (true) {
      const { value, done } = await reader.read(); if (done) break;
      buf += dec.decode(value, { stream: true });
      let i; while ((i = buf.indexOf('\n\n')) >= 0) {
        const line = buf.slice(0, i).replace(/^data: /, ''); buf = buf.slice(i + 2);
        if (!line) continue;
        const ev = JSON.parse(line);
        if (ev.type === 'token') {
          if (!agentLive) { agentLive = true; setStatus('agent live', true); }  // verifiable handshake
          acc += ev.text;
          if (inDossier) window.dossier.onToken(acc);
          else { bubble.innerHTML = renderMarkdown(stripSpec(acc)); scrollLog(); }
        }
        else if (ev.type === 'error') {
          if (inDossier) window.dossier.onError(ev.message);
          else { acc += '\n\n**[error]** ' + ev.message; bubble.innerHTML = renderMarkdown(stripSpec(acc)); }
        }
        else if (ev.type === 'done') {
          // The shelf drawer stays truthful in BOTH skins (§4.4: it's the kept overlay).
          if (ev.studio && typeof window.shelfSync === 'function') window.shelfSync(ev.studio);
          if (inDossier) {
            window.dossier.onDone(ev);
            continue;
          }
          // ?ui=chat / architect: the landed behavior, byte-for-byte.
          if (ev.spec && !window.onboardingActive) renderBlueprint(ev.spec);
          if (MODE === 'workshop' && !window.onboardingActive) renderAgentPanel(ev.studio);
          if (ev.studio && ev.studio.ask) {
            if (!window.onboardingActive) renderAskCard(ev.studio.ask);
            else window._pendingAsk = ev.studio.ask;
          }
        }
      }
    }
  } catch (e) {
    // gate-2 I6: server death mid-turn — queueSend's .catch(()=>{}) swallows the
    // rejection, so the failure must surface HERE: the dossier gets its brass line +
    // re-armed writing line; the chat skin gets an error bubble. The stored session id
    // is NEVER touched on a network failure — only a beats 404 clears it (tryReplay),
    // so a reload after the server returns still resumes the same session.
    const msg = (e && e.message) || 'connection lost — is the studio still running?';
    if (inDossier) window.dossier.onError(msg);
    else if (bubble) { acc += '\n\n**[error]** ' + msg; bubble.innerHTML = renderMarkdown(stripSpec(acc)); }
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

// ── "Your agent" panel (workshop mode) — the conversation's live mirror ──
let catalogCache = null;
async function getCatalog() {
  if (!catalogCache) {
    try { catalogCache = await (await fetch('/api/catalog')).json(); }
    catch { catalogCache = { baseline: { items: [] }, shelf: { items: [] } }; }
  }
  return catalogCache;
}

async function renderAgentPanel(studio) {
  const cat = await getCatalog();
  const byId = new Map((cat.shelf?.items || []).map((i) => [i.id, i]));
  const picks = (studio?.picks || []).map((id) => byId.get(id)).filter(Boolean);
  const ints = [...new Set(picks.flatMap((i) => i.requires || []))];
  const row = (name, tagLabel, locked) =>
    `<div class="ya-row ${locked ? 'locked' : ''}"><span>${name}</span><span class="ya-tag">${tagLabel}</span></div>`;
  // A participant's typed-but-unsent name must survive the next re-render (each chat
  // turn calls this fresh); only fall back to the agent's suggested name when the
  // field is untouched. Mirrors shelf.js's renderBody() keep/restore idiom.
  const keep = $('#ya-name')?.value?.trim();
  $('#blueprint').innerHTML = DOMPurify.sanitize(`
    <div class="bp-card ya">
      <h3>Your agent</h3>
      ${(cat.baseline?.items || []).map((b) => row(b.name, '🔒 baseline', true)).join('')}
      ${picks.length
        ? picks.map((p) => row(p.name, p.cost?.label || '', false)).join('')
        : '<p class="ya-empty">Talk to the architect — your agent takes shape here.</p>'}
      <h3>Integrations</h3>
      <div class="ya-ints">${ints.length ? ints.map((i) => `<span class="int-chip">${i}</span>`).join('') : '<span class="ya-empty">none yet</span>'}</div>
      <label class="kr-field">Agent name
        <input id="ya-name" type="text" maxlength="60" value="${escAttr(keep || studio?.name || '')}" placeholder="e.g. my-cos"></label>
      <button type="button" id="ya-build" ${picks.length ? '' : 'disabled'}>Build my agent ▶</button>
    </div>`);
  const build = $('#ya-build');
  if (build) build.addEventListener('click', () => {
    if (typeof window.shelfBuild === 'function') window.shelfBuild($('#ya-name').value.trim());
  });
}

$('#composer').addEventListener('submit', (e) => {
  e.preventDefault(); const v = $('#msg').value.trim(); if (!v) return;
  $('#msg').value = ''; queueSend(v);
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
  // D0's raw-skills form: no marketplace, no restart (lean spec §5). The install field
  // is `cd <dir> ; claude` (gate-2 S4 — `;` parses in PS 5.1 where `&&` doesn't); the
  // existing ' ; ' split renders it as two lines: cd, then claude.
  return `<pre class="install">${ev.install.split(' ; ').join('\n')}</pre>
    <p>Your agent lives in that folder — run this in a terminal and talk to it.</p>`;
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
  // gate-2 C2: the dossier takeover hides .rightrail, which contains #buildpanel — a
  // drawer build there would stream into a display:none subtree. Until D1c relocates
  // the panel into the closing chapter, float the rail as a fixed dock (the Task 8
  // onboarding-dock pattern). Self-retiring: D1c's beginBuild moves #buildpanel OUT of
  // .rightrail before calling streamBuild, so the condition stops matching.
  const bp = document.getElementById('buildpanel');
  if (UI === 'dossier' && bp && bp.closest('.rightrail')) {
    document.body.classList.add('dz-dock-build');
    bp.hidden = false;
  }
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
window.streamBuild = streamBuild;

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
  setStatus('loaded');
});

start();
