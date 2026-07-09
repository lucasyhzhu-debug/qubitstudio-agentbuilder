// The architect journey — Door B (build any agent) and Door C (build one skill).
// app.js routes chat-stream events here when the journey skin is active. Same backend as
// the legacy ?mode=architect chat: a tool-less `claude -p` architect interview that emits
// the FULL architecture spec each turn in a ```spec fence (extract_spec → session.spec →
// ev.spec on done). This module turns that stream into a dossier-style living document —
// a flowing conversation, a live blueprint of component cards, an "add a skill" action,
// and a build ceremony over the REAL M2→M4 exporter (/api/export → dist/<name>.plugin).
// It reuses the dossier's global CSS classes and app.js's streamBuild / wireKeyRow seams;
// it never touches Door A (dossier) or its ```studio channel.
(function () {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const cssEsc = (s) => (window.CSS && CSS.escape) ? CSS.escape(s) : String(s).replace(/"/g, '\\"');
  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  let skipping = false;
  const beatWait = async (ms) => { if (!skipping && !REDUCED) await sleep(ms); };

  // The seeds that open each door's interview. Door C constrains the architect to a single
  // skill component via the seed alone — the system prompt stays byte-identical (test-locked).
  const SEEDS = {
    build: 'Begin the agent-architect interview.',
    skill: 'I want to build a single standalone skill — not a multi-part agent. Interview me only '
      + 'about this one skill: what it does, when it should trigger, and whether it needs scripts '
      + 'or reference files. Emit a spec with exactly ONE component of type "skill", and do not '
      + 'propose agents, commands, or MCP servers.',
  };
  const PHASES = ['design', 'shape', 'build', 'connect'];

  let kind = 'build';
  let spec = null;             // last extracted architecture spec (ev.spec)
  let chapters = [];           // [{ n, title, phase, el, bodyEl }]
  let open = null;             // the open conversation section
  let acc = '';                // this turn's accumulated raw prose (fences included)
  let building = false, signed = false;
  let lastDone = null;         // the export done event (grade + plugin_path)
  let closeRec = null;         // the Sign & build section
  let prevSpecJson = null;     // for flash-on-change

  // ── activation / boot ─────────────────────────────────────────────────────
  function activate(k) {
    kind = (k === 'skill') ? 'skill' : 'build';
    document.documentElement.classList.add('journey');
    document.body.classList.add('journey');
    $('#journey').hidden = false;
    if (kind === 'skill') {
      $('#jz-kicker').textContent = 'build a skill';
      $('#jz-h1').textContent = "The skill you're building.";
      $('#jz-lede').textContent = 'Describe what this one skill should do and when it should kick in. '
        + "I'll shape it into a standalone skill you can drop into any agent.";
      $('#jz-input').placeholder = 'describe the skill you want…';
    }
    buildRail();
    if (window.setStatus) window.setStatus('architect');
    wireWriteline();
  }

  async function begin() { await window.startArchitectSession(SEEDS[kind]); }

  async function tryReplay() {
    const sid = sessionStorage.getItem('architect-session');
    if (!sid) return false;
    let out;
    try {
      const r = await fetch(`/api/session/${sid}/beats`);
      if (r.status === 404) { sessionStorage.removeItem('architect-session'); return false; }
      if (!r.ok) return false;
      out = await r.json();
    } catch { return false; }
    if (!out.beats || !out.beats.length) return false;
    window.resumeSession(sid);
    out.beats.forEach((b) => {
      const u = String(b.user || '');
      const isSeed = (u === SEEDS.build || u === SEEDS.skill);
      if (u && !isSeed && !/^\[(card|studio event)\]/.test(u)) fossilize(u);
      const prose = window.stripSpec(b.prose || '');
      if (prose.trim()) settleProse(prose, false);
    });
    if (out.last_compose) lastDone = out.last_compose;
    // architect beats don't carry the spec — pull the current one.
    try {
      const s = await (await fetch(`/api/spec?session_id=${encodeURIComponent(sid)}`)).json();
      if (s && s.spec) { spec = s.spec; renderBlueprint(); }
    } catch { /* no spec extracted yet */ }
    if (buildable() && !closeRec) renderClose();
    updateRail();
    armWriteline(true);
    return true;
  }

  // ── streaming (driven by app.js send()) ───────────────────────────────────
  function onToken(full) {
    acc = full;
    holdWriteline();
    $('#jz-live').innerHTML = window.renderMarkdown(window.stripSpec(full));
    liveEdge();
  }

  function onError(msg) {
    if (!open) newSection('Designing your agent', 'design');
    const line = document.createElement('div');
    line.className = 'dz-error';
    line.textContent = '⚠ ' + String(msg || 'something went wrong — write to continue');
    open.bodyEl.appendChild(line);
    $('#jz-live').innerHTML = ''; acc = '';
    armWriteline(true); nudge();
  }

  function onDone(ev) {
    settleStaged();
    if (ev && ev.spec) { spec = ev.spec; renderBlueprint(); }
    if (buildable() && !closeRec && !signed) renderClose();
    updateRail();
    if (!building) armWriteline(true);
    nudge();
  }

  function settleStaged() {
    const staged = $('#jz-live');
    if (staged.innerHTML.trim()) settleProse(staged.innerHTML, true);
    staged.innerHTML = ''; acc = '';
  }
  function settleProse(content, isHtml) {
    const rec = open || newSection('Designing your agent', 'design');
    const prose = document.createElement('div');
    prose.className = 'dz-prose';
    prose.innerHTML = isHtml ? content : window.renderMarkdown(content);
    rec.bodyEl.appendChild(prose);
  }

  function newSection(title, phase) {
    const n = chapters.length + 1;
    const sec = document.createElement('section');
    sec.className = 'dz-sec settle';
    sec.dataset.phase = phase;
    sec.innerHTML = `<div class="sec-head"><span class="no">${String(n).padStart(2, '0')}</span>
      <h2>${esc(title)}</h2><span class="why">${esc(phase)}</span></div>
      <div class="dz-body"></div>`;
    $('#jz-chapters').appendChild(sec);
    const rec = { n, title, phase, el: sec, bodyEl: sec.querySelector('.dz-body') };
    chapters.push(rec); open = rec;
    return rec;
  }

  function fossilize(text) {
    const rec = open || newSection('Designing your agent', 'design');
    const a = document.createElement('div');
    a.className = 'answer';
    a.innerHTML = `<span>${esc(text)}</span>`;   // .answer::before adds the brass dash
    rec.bodyEl.appendChild(a);
  }

  // ── the live blueprint (component cards, updated in place) ─────────────────
  function buildable() {
    return !!(spec && spec.plugin && spec.plugin.name && (spec.components || []).length);
  }

  function renderBlueprint() {
    const host = $('#jz-blueprint');
    if (!host) return;
    const p = (spec && spec.plugin) || {};
    const comps = (spec && spec.components) || [];
    const rt = (spec && spec.runtime) || {};
    const cur = JSON.stringify(spec || {});
    const card = (c) => `<div class="dz-card" data-comp="${esc((c.type || '') + ':' + (c.name || c.id || ''))}">
      <span class="tag">${esc(c.type || 'component')}</span>
      <h3>${esc(c.name || c.id || 'component')}</h3>
      <p>${esc(c.purpose || c.description_seed || c.trigger_intent || '')}</p></div>`;
    const rtList = (arr, f) => (arr && arr.length) ? arr.map(f).join('') : '';
    const inner =
      `<div class="jz-bp-head"><h2>${esc(kind === 'skill' ? 'Your skill' : 'The agent so far')}</h2>
        <button type="button" class="jz-addskill" id="jz-addskill">+ add a skill</button></div>` +
      (p.name
        ? `<p class="jz-identity"><b>${esc(p.name)}</b> — ${esc(p.description || '')}</p>`
        : '<p class="jz-empty">Your agent takes shape here as you talk to the architect.</p>') +
      (comps.length ? `<div class="dz-cards">${comps.map(card).join('')}</div>` : '') +
      ((rt.storage || rt.memory || rt.routines)
        ? `<div class="dz-note">` + [
            rtList(rt.storage, (s) => `<div>storage · ${esc(s.what)} → ${esc(s.where)}</div>`),
            rtList(rt.memory, (m) => `<div>memory · ${esc(m.fact_type)}: ${esc(m.note)}</div>`),
            rtList(rt.routines, (r) => `<div>routine · ${esc(r.name)} (${esc(r.schedule)})</div>`),
          ].join('') + `</div>`
        : '');
    host.innerHTML = window.DOMPurify ? window.DOMPurify.sanitize(inner) : inner;

    if (prevSpecJson && prevSpecJson !== cur) {
      host.querySelectorAll('.dz-card').forEach((c) => {
        c.classList.add('flash'); setTimeout(() => c.classList.remove('flash'), 900);
      });
    }
    prevSpecJson = cur;
    const add = $('#jz-addskill');
    if (add) add.addEventListener('click', openSkillForm);
    if (closeRec && !signed) refreshManifest();
  }

  // "Add a skill" — the UI can't mutate session.spec (the next ```spec overwrites it), so
  // this is a structured message asking the architect to fold in a type:"skill" component
  // and re-emit the FULL spec. Same accepted pattern as the shelf's [studio event] sync.
  function openSkillForm() {
    if ($('#jz-skillform')) return;
    const form = document.createElement('div');
    form.className = 'jz-skillform'; form.id = 'jz-skillform';
    form.innerHTML = `
      <label>Skill name<input id="jz-sk-name" placeholder="e.g. changelog-writer" autocomplete="off"></label>
      <label>What it does<input id="jz-sk-purpose" placeholder="what the skill accomplishes" autocomplete="off"></label>
      <label>When it should trigger<input id="jz-sk-trigger" placeholder="phrases or situations that should invoke it" autocomplete="off"></label>
      <div class="jz-sf-foot">
        <button type="button" class="jz-sf-cancel" id="jz-sk-cancel">cancel</button>
        <button type="button" class="jz-sf-add" id="jz-sk-add">add to agent</button>
      </div>`;
    $('#jz-blueprint').appendChild(form);
    $('#jz-sk-name').focus();
    $('#jz-sk-cancel').addEventListener('click', () => form.remove());
    $('#jz-sk-add').addEventListener('click', () => {
      const nm = $('#jz-sk-name').value.trim();
      const pu = $('#jz-sk-purpose').value.trim();
      const tr = $('#jz-sk-trigger').value.trim();
      if (!nm) { $('#jz-sk-name').focus(); return; }
      form.remove();
      window.queueSend(`[studio event] Add a component of type "skill" named "${nm}"`
        + (pu ? `, purpose: ${pu}` : '') + (tr ? `, trigger intent: ${tr}` : '')
        + '. Then re-emit the FULL updated spec including this new skill component.');
    });
  }

  // ── the close: sign & build ───────────────────────────────────────────────
  function renderClose() {
    closeRec = newSection(kind === 'skill' ? 'Build your skill' : 'Sign & build', 'build');
    closeRec.el.classList.add('closing');
    closeRec.bodyEl.innerHTML = `
      <div class="manifest" id="jz-manifest"></div>
      <div class="sig-row">
        <div class="sigline"><div class="name" id="jz-signame"></div>
          <div class="cap">${kind === 'skill' ? 'this is the skill I want' : 'this is the agent I want'}</div></div>
        <button type="button" class="buildbtn" id="jz-build">Build ${kind === 'skill' ? 'my skill' : 'my agent'}<i>▶</i></button>
      </div>
      <div id="jz-beat-host"></div>`;
    refreshManifest();
    $('#jz-build').addEventListener('click', beginBuild);
    nudge();
  }

  function refreshManifest() {
    const el = $('#jz-manifest');
    if (!el || !spec) return;
    const comps = spec.components || [];
    el.innerHTML = comps.map((c) => `<span class="m">${esc(c.name || c.id)} · ${esc(c.type)}</span>`).join('');
    const nm = $('#jz-signame'); if (nm) nm.textContent = (spec.plugin || {}).name || '';
    const btn = $('#jz-build'); if (btn) btn.disabled = !buildable();
  }

  function icon(t) {
    return t === 'skill' ? '🧩' : t === 'agent' ? '🤖' : t === 'command' ? '⌨️' : t === 'mcp' ? '🔌' : '📦';
  }

  // The build ceremony over the REAL exporter — organs tick on component markers, never timers.
  async function beginBuild() {
    if (building || !buildable()) return;
    building = true; signed = true; skipping = false;
    const comps = spec.components || [];
    const name = spec.plugin.name;
    const skip = $('#jz-skip'); skip.hidden = false; skip.onclick = () => { skipping = true; };
    holdWriteline();

    // beat 1 — the signing
    const nm = $('#jz-signame'); nm.innerHTML = `<b>${esc(name)}</b>`;
    closeRec.el.classList.add('signing');
    const btn = $('#jz-build'); btn.disabled = true; btn.textContent = '✓ signed';
    await beatWait(1400);

    // beat 2 — assembly: one organ per component, ticked by exporter markers (key = <type>:<name>)
    const host = $('#jz-beat-host');
    const organs = comps.map((c) => ({ key: `${c.type}:${c.name}`, ic: icon(c.type), name: c.name || c.id, sub: c.type }));
    host.innerHTML = `<div class="dz-beat on"><div class="beatcap">■ building ${esc(name)}</div>
      <div class="anatomy">${organs.map((o) => `<div class="organ" data-key="${esc(o.key)}">
        <span class="ic">${o.ic}</span><div><b>${esc(o.name)}</b><span>${esc(o.sub)}</span></div>
        <span class="tick">✓</span></div>`).join('')}</div>
      <div class="dz-blog" id="jz-blog"></div><div class="jz-stages" id="jz-stages"></div></div>`;
    host.scrollIntoView({ behavior: 'smooth', block: 'center' });

    const tick = (key, cap) => {
      const o = host.querySelector(`.organ[data-key="${cssEsc(key)}"]`);
      if (o && (String(cap).endsWith('ok') || String(cap).endsWith('running'))) o.classList.add('in');
      if (cap) $('#jz-blog').insertAdjacentHTML('afterbegin', `<div>$ ${esc(cap)}</div>`);
    };
    let doneEv = null, failedEv = null;
    try {
      await window.streamBuild('/api/export', { session_id: window.getSessionId(), run_evals: false }, {
        onEvent: (ev) => {
          if (ev.type === 'component') tick(ev.key, `${ev.key} → ${ev.status}`);
          if (ev.type === 'stage') { const s = $('#jz-stages'); if (s) s.textContent = ev.name + ' · ' + ev.status; }
          if (ev.type === 'log') $('#jz-blog').insertAdjacentHTML('afterbegin', `<div>$ ${esc(ev.text)}</div>`);
          if (ev.type === 'done') doneEv = ev;
          if (ev.type === 'error') failedEv = ev;
        },
      });
    } catch (e) { skip.hidden = true; unbuild('build', String(e)); return; }
    if (failedEv) { skip.hidden = true; unbuild(failedEv.stage, failedEv.message, failedEv.handoff); return; }
    lastDone = doneEv;
    await beatWait(700);

    renderLaunchCard(name);
    renderConnect();
    skip.hidden = true; building = false;
    if (window.setStatus) window.setStatus(`${name} · built`, true);
    updateRail();
    armWriteline(true);
    nudge();
  }

  function renderLaunchCard(name) {
    const host = $('#jz-beat-host'); if (!host) return;
    const grade = (lastDone && lastDone.grade) || 'built';
    const path = (lastDone && lastDone.plugin_path) || '';
    const note = kind === 'skill'
      ? `<div class="try"><div class="t">use your skill</div>
          <div>your skill lives inside the built plugin under <code>skills/&lt;name&gt;/</code></div>
          <div>copy that folder into any agent's <code>.claude/skills/</code> and restart Claude Code</div></div>`
      : `<div class="try"><div class="t">install your agent</div>
          <div>add the plugin to your Claude Code plugins and restart</div>
          <div>then talk to it — it runs the skills you designed</div></div>`;
    host.innerHTML = `<div class="dz-beat on"><div class="beatcap">■ ${kind === 'skill' ? 'your skill' : 'your agent'}</div>
      <div class="launch">
        <div class="lk">${esc(grade)} · built ${new Date().toISOString().slice(0, 10)}</div>
        <h3>${esc(name)}</h3>
        <div class="cmd"><code>${esc(path)}</code><button type="button" id="jz-copy">COPY</button></div>
        ${note}
      </div></div>`;
    const copy = $('#jz-copy');
    if (copy) copy.addEventListener('click', function () {
      if (navigator.clipboard && path) navigator.clipboard.writeText(path);
      this.textContent = 'COPIED ✓';
    });
  }

  // Connect step — integrations come from the spec's mcp components (not a fixed catalog).
  // Known integrations get a live paste-and-test row (reusing wireKeyRow); arbitrary MCP
  // servers get an informational row pointing at the generated INSTALL/SETUP.
  function renderConnect() {
    const mcps = ((spec && spec.components) || []).filter((c) => c.type === 'mcp');
    if (!mcps.length) return;
    const sec = newSection('Connect integrations', 'connect');
    const known = window.KNOWN_INTEGRATIONS || new Set();
    const path = lastDone && lastDone.plugin_path;
    mcps.forEach((c) => {
      const server = String(c.server_name || c.name || '').toLowerCase();
      const match = [...known].find((k) => server.includes(k));
      if (match && path && window.keyRowHtml && window.wireKeyRow) {
        const hostEl = document.createElement('div');
        hostEl.className = 'dz-keyhost';
        hostEl.innerHTML = window.keyRowHtml(match);
        sec.bodyEl.appendChild(hostEl);
        window.wireKeyRow(hostEl.firstElementChild, match, path, () => {});
      } else {
        sec.bodyEl.insertAdjacentHTML('beforeend',
          `<div class="dz-note">${esc(c.server_name || c.name || 'integration')} — set up `
          + `${esc(c.auth_owner || 'its credentials')} at home; see the generated INSTALL/SETUP in your plugin.</div>`);
      }
    });
    nudge();
  }

  function unbuild(stage, message, handoff) {
    building = false; signed = false;
    if (closeRec) closeRec.el.classList.remove('signing');
    const btn = $('#jz-build');
    if (btn) { btn.disabled = false; btn.textContent = `Build ${kind === 'skill' ? 'my skill' : 'my agent'} ▶`; }
    const host = $('#jz-beat-host');
    if (host) {
      host.innerHTML = `<div class="dz-error">✗ ${esc(stage || 'build')}: ${esc(message || 'the build could not finish')}</div>`;
      if (handoff) host.insertAdjacentHTML('beforeend',
        `<div class="dz-note">A supervised fallback was written to <code>${esc(handoff.spec_path)}</code> — `
        + `run <code>/agent-architect</code> in your own session to finish it.</div>`);
    }
    armWriteline(true); nudge();
  }

  // ── the writing line ──────────────────────────────────────────────────────
  function wireWriteline() {
    const form = $('#jz-writeline'); const input = $('#jz-input');
    if (!form || !input) return;
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const v = input.value.trim();
      if (!v || input.disabled) return;
      input.value = '';
      fossilize(v);
      holdWriteline();
      window.queueSend(v);
    });
  }
  function armWriteline(hot) {
    const form = $('#jz-writeline'); const input = $('#jz-input');
    if (!form || !input) return;
    form.classList.toggle('held', !hot);
    input.disabled = !hot;
    if (hot && !skipping) input.focus();
  }
  function holdWriteline() { armWriteline(false); }

  // ── the journey rail ──────────────────────────────────────────────────────
  function buildRail() {
    const rail = $('#jz-rail'); if (!rail) return;
    rail.innerHTML = '<i></i>' + PHASES.map((p) =>
      `<span class="node" data-phase="${esc(p)}"><b></b><span>${esc(p)}</span></span>`).join('');
    rail.querySelectorAll('.node').forEach((n, i) => {
      n.style.top = (10 + i * (80 / Math.max(1, PHASES.length - 1))) + '%';
    });
    updateRail();
  }
  function updateRail() {
    const rail = $('#jz-rail'); if (!rail) return;
    let phase = 'design';
    if (buildable()) phase = 'shape';
    if (closeRec) phase = 'build';
    if (lastDone) phase = 'connect';
    const idx = PHASES.indexOf(phase);
    rail.querySelectorAll('.node').forEach((n, i) => {
      n.classList.toggle('done', i < idx);
      n.classList.toggle('now', i === idx);
    });
    const fill = rail.querySelector('i');
    if (fill) fill.style.height = (idx / Math.max(1, PHASES.length - 1) * 80) + '%';
  }

  // gentle scroll helpers — the live edge follows the stream; settle nudges the tail in
  function liveEdge() { const l = $('#jz-live'); if (l) l.scrollIntoView({ behavior: 'auto', block: 'nearest' }); }
  function nudge() { const w = $('#jz-writeline'); if (w) w.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }

  window.journey = { activate, begin, tryReplay, onToken, onError, onDone };
})();
