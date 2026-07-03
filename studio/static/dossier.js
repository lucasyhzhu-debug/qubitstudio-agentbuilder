// The dossier — the workshop page as a living document (dossier spec §4).
// app.js routes chat-stream events here when the dossier skin is active; every beat is
// still one `claude -p` turn under the hood. Rendering model (§4.1): tokens stream into
// the headless #dz-live staging block at the document's live edge; the `chapter` field
// settles heading + placement at done (same title continues the open section, new title
// opens a numbered one, no valid chapter folds into the open section).
(function () {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const norm = (t) => String(t || '').trim().toLowerCase();
  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  let skipping = false;
  const beatWait = async (ms) => { if (!skipping && !REDUCED) await sleep(ms); };
  const PHASES = ['welcome', 'baseline', 'skills', 'personalize', 'name', 'build', 'connect'];

  let chapters = [];        // [{ n, title, phase, el, bodyEl }] in document order
  let open = null;          // the open (last) chapter record
  let prevPicks = [];       // previous beat's picks — drives the picks-diff (§4.1.1)
  let pendingDiff = null;   // picks that arrived before the catalog (gate-2 R7)
  let lastStudio = null;    // last settled whole-state studio block
  let lastDone = null;      // last compose done event — set by D1c builds (Task 15/16),
                            // RESTORED on reload from the beats payload's last_compose
                            // (gate-2 S6); Task 18's key-field blocks read it
  let catalog = null;
  let pendingAsk = null;    // the unanswered ask at the tail, if any
  let acc = '';             // this turn's accumulated raw prose (fences included)
  let replaying = false;
  let busy = false;         // a turn is queued/in flight (gate-2 I1) — the D1b verbs gate on it
  // Set by the D1b revision verbs; consumed by exactly ONE settle (§5 pending-target
  // override): { rec, mode: 'append' | 'replace' }.
  let pendingTarget = null;
  let rwSettle = null;      // D1b: deferred re-settle to run on the rewrite beat's done
  let closeRec = null;      // the signature-close chapter record (D1c)
  let building = false;
  let signed = false;
  let chipObserver = null;  // the launch-card chip observer — one per build, always
                            // disconnected before re-observe and in unsign (gate-2 S10)

  // The two seeds the studio ever sends (gate-2 S9: exact match, never a prefix guess —
  // a participant's own line starting with "Begin " must fossilize).
  const SEED_MSGS = ['Begin the workshop interview.', 'Begin onboarding.'];

  // Every dossier-originated send marks the turn in flight the moment it QUEUES
  // (gate-2 I1); onToken re-asserts it for turns other surfaces queue (shelf events,
  // onboarding events). onDone/onError clear it.
  const sendTurn = (msg) => { busy = true; return window.queueSend(msg); };

  // ── activation ──────────────────────────────────────────────────────────
  async function activate() {
    window.dossierActive = true;
    document.documentElement.classList.add('dossier');
    document.body.classList.add('dossier');
    $('#dossier').hidden = false;
    buildRail();
    // gate-2 R7: the catalog must be in hand before the first done's picks-diff —
    // start() awaits activate; a diff that somehow lands first parks in pendingDiff
    // and re-runs here on arrival.
    await getCatalog();
    if (pendingDiff) { const p = pendingDiff; pendingDiff = null; diffPicks(p); }
  }

  async function getCatalog() {
    if (!catalog) {
      try { catalog = await (await fetch('/api/catalog')).json(); }
      catch { catalog = { baseline: { items: [] }, shelf: { items: [] } }; }
    }
    return catalog;
  }
  const shelfById = () => new Map((((catalog || {}).shelf || {}).items || []).map((i) => [i.id, i]));

  // ── beats replay (spec §4.1: a reload against a live server restores the page) ──
  async function tryReplay() {
    const sid = sessionStorage.getItem('dossier-session');
    if (!sid) return false;
    let out;
    try {
      const r = await fetch(`/api/session/${sid}/beats`);
      if (r.status === 404) {
        // gate-2 I6: only a DEFINITIVE "no such session" (the studio restarted)
        // forgets the id — a transient failure must leave it resumable.
        sessionStorage.removeItem('dossier-session');
        return false;
      }
      if (!r.ok) return false;      // transient server trouble — keep the id
      out = await r.json();
    } catch { return false; }       // network failure (server down) — keep the id; a
                                    // reload after the server returns still resumes
    if (!out.beats || !out.beats.length) return false;
    await getCatalog();
    window.resumeSession(sid);
    if (out.last_compose) lastDone = out.last_compose;   // gate-2 S6: launch/connect
                                                         // state survives the reload
    replaying = true;
    out.beats.forEach((b, i) => replayBeat(b, i === out.beats.length - 1));
    replaying = false;
    if (lastStudio && typeof window.shelfSync === 'function') window.shelfSync(lastStudio);
    return true;
  }

  function replayBeat(b, isLast) {
    const u = String(b.user || '');
    if (/^\[studio event\] rewrite — /.test(u)) {
      // gate-2 C3: VERB-AWARE replay — re-apply the rewrite to the already-replayed
      // document, mirroring live beginRewrite/finish: the OLD fossil (rendered by an
      // earlier beat) becomes the NEW answer with the `rewritten ↺` chip, and this
      // beat's prose routes to THAT chapter (one-beat pending target), so a retitled
      // rewrite turn can never open a duplicate section on reload.
      const m = u.match(/^\[studio event\] rewrite — question: "([\s\S]*?)" — previous answer: "([\s\S]*?)" — new answer: "([\s\S]*)"$/);
      if (m) {
        // match by the previous answer's text; prefer a data-q match when one exists
        // (replayed [card] fossils carry no data-q — text alone must suffice)
        const fossils = [...document.querySelectorAll('#dossier .answer')].filter((a) =>
          ((a.firstChild && a.firstChild.textContent) || '').trim() === m[2]);
        const oldFossil = fossils.find((a) => (a.dataset.q || '') === m[1]) || fossils[0];
        if (oldFossil) {
          const sec = oldFossil.closest('.dz-sec');
          const rec = chapters.find((c) => c.el === sec);
          const host = oldFossil.parentNode, before = oldFossil.nextSibling;
          oldFossil.remove();
          const saveOpen = open;
          open = { bodyEl: host };           // retarget so the re-fossil lands in place
          const a = fossilize(m[3], m[1], true);   // 3rd arg = the rewritten chip —
          open = saveOpen;                         // added by Task 13's fossilize; a
          host.insertBefore(a, before);            // 2-arg fossilize (pre-D1b) ignores
          if (rec) pendingTarget = { rec, mode: 'append' };   // it (no verb beats exist then)
        }
      }
    } else if (/^\[studio event\] regenerate chapter "/.test(u)) {
      // gate-2 C3: the regenerate beat's prose REPLACES its chapter's replayed prose —
      // never doubles it. norm-matched by title, exactly like live settle().
      const m = u.match(/^\[studio event\] regenerate chapter "([\s\S]*?)"/);
      const rec = m && chapters.find((c) => norm(c.title) === norm(m[1]));
      if (rec) pendingTarget = { rec, mode: 'replace' };
    } else if (!/^\[studio event\]/.test(u) && !SEED_MSGS.includes(u)) {
      // seeds and [studio event]s are the machine channel — never part of the record;
      // a [card] message re-fossilizes its answer part (flagged deviation 4)
      if (/^\[card\] /.test(u)) {
        const m = u.match(/^\[card\] [\s\S]* → ([\s\S]*)$/);
        fossilize((m ? m[1] : u.slice(7)).replace(/^\(custom\) /, ''));
      } else {
        fossilize(u);
      }
    }
    acc = b.prose || '';
    $('#dz-live').innerHTML = window.renderMarkdown(window.stripSpec(acc));
    // asks/writeline render only on the LAST beat — earlier asks are already answered
    // (their fossil is the record); the pending one re-arms live.
    onDone({ studio: b.studio || {} }, !isLast);
  }

  // ── streaming: the live edge (§4.1) ─────────────────────────────────────
  function onToken(fullText) {
    busy = true;                   // gate-2 I1: verbs stay inert while a turn streams
    acc = fullText;
    holdWriteline();
    $('#dz-live').innerHTML = window.renderMarkdown(window.stripSpec(fullText));
    nudgeScroll();
  }

  // §4.1 errors: a brass error line in the open chapter, the writing line re-arms,
  // any card-held baton releases — the participant can always continue.
  function onError(message) {
    busy = false;
    // gate-2 S1: claude-missing-at-boot is the likeliest room failure — with no open
    // chapter the brass line needs a home that survives the staging wipe below, so
    // the Welcome section opens FIRST.
    if (!open) newSection({ title: 'Welcome', phase: 'welcome' });
    const line = document.createElement('div');
    line.className = 'dz-error';
    line.textContent = '⚠ ' + String(message || 'something went wrong — write to continue');
    open.bodyEl.appendChild(line);
    $('#dz-live').innerHTML = '';
    acc = '';
    pendingTarget = null;          // a verb's target clears on its beat, success or error (§5)
    verbErrorRecover();
    armWriteline(pendingAsk, true);
    nudgeScroll();
  }

  // ── the settle: one done event = one beat (§4.1) ────────────────────────
  function onDone(ev, quiet) {
    busy = false;
    const studio = (ev && ev.studio) || lastStudio || {};
    const rec = settle(studio.chapter);
    if (studio.chapter && studio.chapter.blocks && studio.chapter.blocks.length) {
      renderBlocks(rec, studio.chapter.blocks);   // D2: renders the typed vocabulary after the prose (§3.2)
    }
    diffPicks(studio.picks || []);
    pendingAsk = studio.ask || null;
    // D1b: honest re-settle after a rewrite beat — MUST run BEFORE the ask render,
    // so its '.dz-ask:not([data-answered])' sweep folds only STALE downstream asks;
    // the rewrite beat's own fresh ask renders after, alive (T13 review fix).
    if (rwSettle) { rwSettle(); rwSettle = null; }
    // gate-2 R6: ONE hot surface — while the C3 walk holds the page the ask parks in
    // pendingAsk; renderPendingAsk renders it on handback (Task 10's baton hook).
    if (studio.ask && !quiet && !window.onboardingActive) renderAsk(studio.ask);
    lastStudio = studio;
    if (studio.ready && studio.name && (studio.picks || []).length && !closeRec) renderClose();
    if (closeRec && !signed) refreshManifest();
    // T15 review: a chat turn settling MID-BUILD must not reopen the held document —
    // the build's own completion path (rearmRebuild/unsign) re-arms the writeline.
    if (!quiet && !building) armWriteline(pendingAsk, true);
    updateRail();
    if (!quiet) nudgeScroll();
  }

  function settle(chapter) {
    const staged = $('#dz-live');
    let target;
    if (pendingTarget) {
      // §5 pending-target override: the verb's beat routes to the requested chapter
      // regardless of the emitted title, consuming exactly one beat.
      target = pendingTarget;
      pendingTarget = null;
    } else if (chapter && open && norm(chapter.title) === norm(open.title)) {
      target = { rec: open, mode: 'append' };        // same title → the staging is invisible
    } else if (chapter) {
      target = { rec: newSection(chapter), mode: 'append' };
    } else {
      // §3.1 fallback: no valid chapter → staged prose folds into the open chapter;
      // the very first beat with no chapter still opens the welcome section.
      target = { rec: open || newSection({ title: 'Welcome', phase: 'welcome' }), mode: 'append' };
    }
    if (staged.innerHTML.trim()) {
      if (target.mode === 'replace') {
        // regenerate (§5): agent prose only, in place — fossils/asks/cards untouched.
        // .dz-stale-mark rides out with the prose it annotates (gate-2 R1): a
        // regenerated chapter is fresh, its "written before your rewrite" mark stale.
        // [data-block] rides out too (T18 review): the regenerate beat re-runs
        // renderBlocks, so the OLD typed blocks (including any live key row) must go
        // or every block — and its wireKeyRow listener — would double. diffPicks'
        // picks-diff grids never carry the attribute and stay untouched.
        target.rec.bodyEl.querySelectorAll('.dz-prose, .dz-error, .dz-stale-mark, [data-block]')
          .forEach((n) => n.remove());
      }
      const prose = document.createElement('div');
      prose.className = 'dz-prose';
      prose.innerHTML = staged.innerHTML;
      target.rec.bodyEl.appendChild(prose);
    }
    target.rec.el.classList.remove('dz-regenerating');
    staged.innerHTML = '';
    acc = '';
    return target.rec;
  }

  function newSection(ch) {
    const n = chapters.length + 1;
    const sec = document.createElement('section');
    sec.className = 'dz-sec settle';
    sec.dataset.phase = ch.phase;
    sec.dataset.n = n;
    sec.innerHTML = `
      <div class="sec-head"><span class="no">${String(n).padStart(2, '0')}</span>
        <h2>${esc(ch.title)}</h2>
        <button type="button" class="dz-regen" title="rewrite this chapter fresh">⟳</button>
        <span class="why">${esc(ch.phase)}</span></div>
      <div class="dz-body"></div>`;
    $('#dz-chapters').appendChild(sec);
    const rec = { n, title: ch.title, phase: ch.phase, el: sec,
                  bodyEl: sec.querySelector('.dz-body') };
    chapters.push(rec);
    open = rec;
    sec.querySelector('.dz-regen').addEventListener('click', () => {
      if (pendingTarget || rw || busy) return;    // one revision in flight; never while
                                                  // a turn streams (gate-2 I1)
      pendingTarget = { rec, mode: 'replace' };   // §5: replaces agent prose ONLY, in place
      sec.classList.add('dz-regenerating');
      holdWriteline();
      sendTurn(`[studio event] regenerate chapter "${rec.title}" — rewrite it fresh, same facts`);
    });
    return rec;
  }

  // ── D2: the typed block vocabulary (§3.2), interleaved after the beat's prose ──
  function renderBlocks(rec, blocks) {
    // Every node emitted here carries data-block, so a regenerate (§5 replace) can
    // strip a chapter's OLD blocks without touching diffPicks' picks-diff grids
    // (which share .dz-cards but never carry the attribute) — T18 review fix.
    (blocks || []).forEach((b) => {
      if (b.type === 'step') {
        rec.bodyEl.insertAdjacentHTML('beforeend',
          `<div class="dz-step" data-block><b>${esc(String(b.n || '·'))}</b><span>${esc(b.text)}</span></div>`);
      } else if (b.type === 'note') {
        rec.bodyEl.insertAdjacentHTML('beforeend', `<div class="dz-note" data-block>${esc(b.text)}</div>`);
      } else if (b.type === 'checklist') {
        rec.bodyEl.insertAdjacentHTML('beforeend',
          `<div class="dz-checklist" data-block>${b.items.map((i) =>
            `<div class="dz-check">☐ ${esc(i)}</div>`).join('')}</div>`);
      } else if (b.type === 'skill-card') {
        const it = shelfById().get(b.id);
        if (it) rec.bodyEl.insertAdjacentHTML('beforeend',
          `<div class="dz-cards" data-block>${skillCardHtml(it, 'skill')}</div>`);
      } else if (b.type === 'key-field') {
        // hosts the EXISTING connect row (§3.2/§7.2) — never a reimplementation
        if (!window.KNOWN_INTEGRATIONS || !window.KNOWN_INTEGRATIONS.has(b.integration)) return;
        if (!lastDone || !lastDone.plugin_path) {
          rec.bodyEl.insertAdjacentHTML('beforeend',
            '<div class="dz-note" data-block>build first — keys connect after the signing</div>');
          return;
        }
        const host = document.createElement('div');
        host.className = 'dz-keyhost';
        host.setAttribute('data-block', '');
        host.innerHTML = window.keyRowHtml(b.integration);
        const row = host.firstElementChild;
        rec.bodyEl.appendChild(host);
        window.wireKeyRow(row, b.integration, lastDone.plugin_path,
          (ok) => { if (ok) fillChip(b.integration); });   // the launch card completes (§6.5)
      }
      // unknown types never reach here — the extractor drops them (§3.2); the
      // if/else chain skips anything unexpected anyway.
    });
  }

  // ── picks-diff → skill cards (§4.1.1) ───────────────────────────────────
  function skillCardHtml(it, tag) {
    return `<div class="dz-card" data-skill="${esc(it.id)}"><span class="tag">${esc(tag)}</span>
      <h3>${esc(it.name)}</h3><p>${esc(it.what)}</p>
      <span class="price">${esc((it.cost && it.cost.label) || '')}</span></div>`;
  }

  function diffPicks(picks) {
    if (!catalog) { pendingDiff = picks.slice(); return; }   // re-diffed on catalog arrival (gate-2 R7)
    const byId = shelfById();
    const added = picks.filter((id) => !prevPicks.includes(id) && byId.has(id));
    const removed = prevPicks.filter((id) => !picks.includes(id));
    if (added.length && open) {
      const grid = document.createElement('div');
      grid.className = 'dz-cards';
      grid.innerHTML = added.map((id) => skillCardHtml(byId.get(id), '✓ added')).join('');
      open.bodyEl.prepend(grid);       // top of the open chapter (§4.1)
    }
    removed.forEach((id) => {
      const card = document.querySelector(`.dz-card[data-skill="${CSS.escape(id)}"]`);
      if (card) {
        const r = document.createElement('div');
        r.className = 'dz-receipt';
        r.textContent = `– ${id} set aside`;
        card.replaceWith(r);           // fold to a receipt line
      }
    });
    prevPicks = picks.slice();
  }

  // ── D1c: the signature close (§4.1 step 4) ──────────────────────────────
  function renderClose() {
    closeRec = newSection({ title: 'Sign & build', phase: 'build' });
    closeRec.el.classList.add('closing');
    closeRec.bodyEl.innerHTML = `
      <div class="manifest" id="dz-manifest"></div>
      <div class="sig-row">
        <div class="sigline"><div class="name" id="dz-signame"></div>
          <div class="cap">signed — this is the agent I want</div></div>
        <button type="button" class="buildbtn" id="dz-build">Build my agent<i>▶</i></button>
      </div>
      <div id="dz-stagebox"><div id="dz-beat-host"></div>
        <details class="dz-buildlog-wrap" id="dz-rawlog" hidden>
          <summary>raw build log</summary></details></div>`;
    refreshManifest();
    $('#dz-build').addEventListener('click', beginBuild);
    nudgeScroll();
  }

  // §4.4: the manifest renders from STUDIO PICKS ONLY — the shelf event sync keeps the
  // agent's whole-state picks truthful, so the signed manifest cannot diverge.
  function refreshManifest() {
    const el = $('#dz-manifest');
    if (!el || !lastStudio) return;
    const byId = shelfById();
    const base = (((catalog || {}).baseline || {}).items || []);
    el.innerHTML =
      base.map((b) => `<span class="m lock">🔒 ${esc(b.name)}</span>`).join('') +
      (lastStudio.picks || []).map((id) => {
        const it = byId.get(id);
        return it ? `<span class="m">${esc(it.name)}${it.cost && it.cost.label ? ' · ' + esc(it.cost.label) : ''}</span>` : '';
      }).join('');
    const nm = $('#dz-signame');
    if (nm) nm.textContent = lastStudio.name || '';
    const btn = $('#dz-build');
    // §6.1 gating: non-empty picks AND a name — mirrors the existing gates; the
    // server preflight still sits behind it.
    if (btn) btn.disabled = !(lastStudio.name && (lastStudio.picks || []).length);
  }

  // ── D1c: build — the five-beat ceremony (spec §6) ───────────────────────
  async function beginBuild() {
    if (building || !lastStudio) return;
    const picks = (lastStudio.picks || []).slice();
    const name = lastStudio.name;
    if (!picks.length || !name) return;
    building = true; signed = true; skipping = false;
    const byId = shelfById();
    const skipBtn = $('#dz-skip');
    skipBtn.hidden = false;
    skipBtn.onclick = () => { skipping = true; };
    holdWriteline();                    // the document is closed for edits (§6.1)

    // ── BEAT 1: the signing — the name inks itself across the line ──
    const nm = $('#dz-signame');
    nm.innerHTML = `<b>${esc(name)}</b>`;
    closeRec.el.classList.add('signing');
    const btn = $('#dz-build');
    btn.disabled = true; btn.textContent = '✓ signed';
    await beatWait(1600);

    // ── BEAT 2: the binding — the dossier compresses to a ToC card ──
    // Honest theater: these fragments are the participant's real answers, and they
    // genuinely feed the personalize pass (their profile seeded the session).
    const host = $('#dz-beat-host');
    const rows = chapters.filter((c) => c !== closeRec).map((c) => {
      const a = c.bodyEl.querySelector('.answer');
      const frag = a && a.firstChild ? a.firstChild.textContent.trim() : '';
      return `<div class="row"><b>§${String(c.n).padStart(2, '0')} ${esc(c.title.toUpperCase())}</b>` +
        `<i>${frag ? esc('"' + (frag.length > 44 ? frag.slice(0, 41) + '…' : frag) + '"') : ''}</i></div>`;
    }).join('');
    const nAnswers = document.querySelectorAll('#dossier .answer').length;
    host.innerHTML = `
      <div class="dz-beat on">
        <div class="beatcap">■ binding your dossier — everything you told me becomes its memory</div>
        <div class="toc"><h3>The ${esc(name)} dossier</h3>${rows}
          <div class="stamp">${chapters.length - 1} chapters · ${nAnswers} answers · signed ${new Date().toISOString().slice(0, 10)}</div>
        </div></div>`;
    host.scrollIntoView({ behavior: 'smooth', block: 'center' });
    await beatWait(2200);

    // ── BEAT 3: the assembly — organs tick on REAL compose events, never timers (§6.3) ──
    const organs = [
      { key: 'vault', ic: '🧠', name: 'wiki-brain spine', sub: 'its memory — seeded, yours' },
      { key: 'shell', ic: '⚙️', name: 'chief-of-staff shell', sub: 'identity, your voice, read→decide→act' },
      ...picks.map((id) => ({ key: `skill:${id}`, ic: '🧩',
        name: (byId.get(id) || { name: id }).name, sub: (byId.get(id) || {}).what || '' })),
      // what Assembly does NOT claim: per-answer skill personalization is r1-B — the
      // identity organ's caption says only what actually runs (§6.3)
      { key: 'stage:assemble', ic: '✍️', name: 'identity',
        sub: 'owner name + vault path written into every file' },
    ];
    host.innerHTML = `
      <div class="dz-beat on">
        <div class="beatcap">■ assembling ${esc(name)}</div>
        <div class="anatomy">${organs.map((o) => `
          <div class="organ" data-key="${esc(o.key)}"><span class="ic">${o.ic}</span>
            <div><b>${esc(o.name)}</b><span>${esc(o.sub)}</span></div>
            <span class="tick">✓</span></div>`).join('')}</div>
        <div class="dz-blog" id="dz-blog"></div></div>`;
    const panel = $('#buildpanel');
    panel.hidden = false;
    const raw = $('#dz-rawlog');
    raw.hidden = false;
    raw.appendChild(panel);             // truth under the theater — the raw stream stays reachable
    const tick = (key, cap) => {
      const o = host.querySelector(`.organ[data-key="${CSS.escape(key)}"]`);
      if (o) o.classList.add('in');
      if (cap) $('#dz-blog').insertAdjacentHTML('afterbegin', `<div>$ ${esc(cap)}</div>`);
    };
    let doneEv = null, failedEv = null;
    try {
      await window.streamBuild('/api/compose', { picks, name }, {
        onEvent: (ev) => {
          if (ev.type === 'component') tick(ev.key, `${ev.key} → ok`);
          if (ev.type === 'stage' && ev.name === 'assemble' && ev.status === 'ok') {
            tick('stage:assemble', 'owner + vault substitutions applied');
          }
          if (ev.type === 'log') $('#dz-blog').insertAdjacentHTML('afterbegin', `<div>$ ${esc(ev.text)}</div>`);
          if (ev.type === 'done') doneEv = ev;
          if (ev.type === 'error') failedEv = ev;
        },
      });
    } catch (e) {
      // T15 review: a TRANSPORT-level failure (fetch/reader rejects — the server died
      // mid-compose) emits no SSE error event, so it must un-sign HERE — otherwise
      // building/signed stay true and the held document is stuck until reload.
      skipBtn.hidden = true;
      unsign({ stage: 'build', message: String(e) });
      return;
    }
    if (failedEv) { skipBtn.hidden = true; unsign(failedEv); return; }
    lastDone = doneEv;
    await beatWait(900);

    // ── BEAT 4: first breath — the status chip hands over, the agent speaks (§6.4) ──
    host.innerHTML = `
      <div class="dz-beat on dz-breath">
        <span class="dz-chip" id="dz-chip"><i class="dot"></i><span id="dz-chiptext">architect</span></span>
        <div class="firstwords" id="dz-fw"><span id="dz-tw"></span><span class="caret"></span></div>
      </div>`;
    await beatWait(900);
    $('#dz-chiptext').textContent = `${name} · live`;
    $('#dz-chip').classList.add('alive');
    window.setStatus(`${name} · live`, true);           // the header chip hands over too
    const tw = $('#dz-tw');
    let words = '', fbFailed = false;
    try {
      const r = await fetch('/api/first-breath', { method: 'POST' });
      const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = '';
      while (true) {
        const { value, done } = await reader.read(); if (done) break;
        buf += dec.decode(value, { stream: true });
        let i; while ((i = buf.indexOf('\n\n')) >= 0) {
          const line = buf.slice(0, i).replace(/^data: /, ''); buf = buf.slice(i + 2);
          if (!line) continue;
          const ev = JSON.parse(line);
          // tokens paint the moment they arrive — there is no artificial typing
          // cadence here for SKIP to cut (gate-2 S8): the greeting is a real turn,
          // and skipping only removes the staged beatWaits around it.
          if (ev.type === 'token') { words += ev.text; tw.textContent = words; }
          if (ev.type === 'error') fbFailed = true;
        }
      }
    } catch { fbFailed = true; }
    if (fbFailed || !words.trim()) {
      // flagged fallback (§6.4): the ceremony never hangs the room
      $('#dz-fw').innerHTML = `<div class="dz-fw-fallback">“I'm ${esc(name)} — your chief of staff.` +
        ` Run the launch command below and say hello.”` +
        `<span class="dz-fw-flag">offline greeting — the live one meets you in the terminal</span></div>`;
    } else {
      const caret = $('#dz-fw .caret'); if (caret) caret.remove();
    }
    await beatWait(1800);

    // ── BEAT 5: the launch card — real command, chips PENDING (§6.5) ──
    // The old wizard rule gating the install line on connected keys is retired in
    // dossier mode: the command is real from first render; chips carry connect state.
    const ints = (lastDone && lastDone.integrations) || [];
    const base = (((catalog || {}).baseline || {}).items || []);
    const tryLines = picks.slice(0, 3).map((id) => {
      const it = byId.get(id) || {};
      const ask = ((it.brief || '').split('—')[1] || it.what || id).trim().split('.')[0];
      return `<div>“${esc(ask)}” — makes ${esc(it.deliverable || 'its first move')}</div>`;
    }).join('');
    host.innerHTML = `
      <div class="dz-beat on">
        <div class="beatcap">■ your agent</div>
        <div class="launch">
          <div class="lk">agent · built ${new Date().toISOString().slice(0, 10)}</div>
          <h3>${esc(name)}</h3>
          <div class="parts">${base.map((b) => `<span class="m lock">🔒 ${esc(b.name)}</span>`).join('')}
            ${picks.map((id) => `<span class="m">${esc((byId.get(id) || { name: id }).name)}</span>`).join('')}</div>
          <div class="ints" id="dz-launch-ints">${ints.length
            ? ints.map((i) => `<span class="dz-int pending" data-int="${esc(i)}">${esc(i)} · pending</span>`).join(' ')
            : 'no integrations needed — fully local'}</div>
          <div class="cmd"><code>${((lastDone && lastDone.install) || '')
            // flagged deviation 11 (the installLineHtml precedent, app.js): the
            // `cd <dir> ; claude` one-liner DISPLAYS as two lines — each segment
            // esc'd before the <br> join, so the path never lands as raw HTML.
            .split(' ; ').map(esc).join('<br>')}</code>
            <button type="button" id="dz-copy">COPY</button></div>
          <div class="try"><div class="t">three things to ask it first</div>${tryLines}</div>
        </div></div>`;
    $('#dz-copy').addEventListener('click', function () {
      if (navigator.clipboard && lastDone) navigator.clipboard.writeText(lastDone.install);
      this.textContent = 'COPIED ✓';
    });
    // chips fill live as the embedded connect rows pass their smoke tests. D1c watches
    // the wizard rows' class flips; D2's wireKeyRow onResult supersedes this trigger
    // for chapter rows (the observer stays for the embedded wizard fallback rows).
    // gate-2 S10: ONE observer per build — disconnect any previous one first (unsign
    // also disconnects on the failure path).
    if (chipObserver) chipObserver.disconnect();
    chipObserver = new MutationObserver(() => {
      panel.querySelectorAll('.keyrow.kr-pass').forEach((row) => fillChip(row.dataset.int));
    });
    chipObserver.observe(panel, { attributes: true, subtree: true, attributeFilter: ['class'] });
    skipBtn.hidden = true;
    skipping = false;
    building = false;
    rearmRebuild();                     // gate-2 S2: the ceremony ends with Rebuild live
    armWriteline(pendingAsk, true);     // …and the writing line hot — the journey hands
                                        // into the connect chapters (D2) by conversation
    nudgeScroll();
  }

  // a launch-card integration chip completes (§6.5) — shared with D2's key-field blocks
  function fillChip(integration) {
    const chip = document.querySelector(`.dz-int[data-int="${CSS.escape(integration)}"]`);
    if (chip && chip.classList.contains('pending')) {
      chip.classList.remove('pending');
      chip.classList.add('ok');
      chip.textContent = `${integration} ✓`;
    }
  }

  // gate-2 S2: after a SUCCESSFUL build the ceremony leaves REBUILD executable —
  // `signed` resets (so refreshManifest re-applies the §6.1 gates and keeps updating
  // the manifest), the button re-arms as "Rebuild", and the consequence warning sits
  // beside it: connected keys (.env) are re-entered; the vault survives (gate-2 I4).
  function rearmRebuild() {
    signed = false;
    const btn = $('#dz-build');
    btn.disabled = false;
    btn.textContent = 'Rebuild ▶';
    if (!closeRec.el.querySelector('.dz-rebuild-warn')) {
      const warn = document.createElement('div');
      warn.className = 'dz-rebuild-warn';
      warn.textContent = 'rebuilding recreates the home — re-enter connected keys (.env); ' +
        'your agent’s vault (its memory) is preserved';
      btn.after(warn);
    }
    refreshManifest();
  }

  // §6.1: a composer error renders INSIDE the ceremony with an un-sign/retry — the
  // signature un-inks and the document reopens for edits.
  function unsign(ev) {
    building = false; signed = false;
    if (chipObserver) { chipObserver.disconnect(); chipObserver = null; }   // gate-2 S10
    const panel = $('#buildpanel');
    document.querySelector('.rightrail').appendChild(panel);   // give the node back
    panel.hidden = true;
    closeRec.el.classList.remove('signing');
    $('#dz-rawlog').hidden = true;
    $('#dz-beat-host').innerHTML =
      `<div class="dz-error">⚠ ${esc(ev.stage || 'build')}: ${esc(ev.message || 'failed')}` +
      ` — un-signed. Fix it (rewrite an answer, reopen the shelf) and build again.</div>`;
    const btn = $('#dz-build');
    btn.textContent = 'Build my agent ▶';
    refreshManifest();                  // re-enables per the gates
    armWriteline(pendingAsk, true);     // the document reopens
  }

  // ── inline asks: the ask channel as dossier material (§4.1.2) ───────────
  function renderAsk(ask) {
    if (!open) newSection({ title: 'Welcome', phase: 'welcome' });
    if (open.bodyEl.querySelector(`.dz-ask[data-ask-id="${CSS.escape(ask.id)}"]:not([data-answered])`)) return;
    const wrap = document.createElement('div');
    wrap.className = 'dz-ask';
    wrap.dataset.askId = ask.id;
    wrap.innerHTML = `
      <div class="ask"><div class="who">architect asks</div><p>${esc(ask.title)}</p></div>
      <div class="choices">${ask.options.map((o) => `
        <button type="button" class="choice" data-oid="${esc(o.id)}">
          <b>${esc(o.label)}</b><span>${esc(o.why || '')}</span></button>`).join('')}</div>
      <div class="or">or write your own ↓</div>`;
    open.bodyEl.appendChild(wrap);
    wrap.querySelectorAll('.choice').forEach((c) => c.addEventListener('click', () => {
      if (wrap.dataset.answered) return;
      const o = ask.options.find((x) => x.id === c.dataset.oid);
      if (o) answerAsk(ask, wrap, o.label, c.dataset.oid);
    }));
  }

  // One hot surface (the onboarding-cards baton rule, §4.1.2): the cards and the
  // writing line together are the ask's answer surface; answering by either
  // fossilizes, sends the [card] message, and holds the line until the next done.
  function answerAsk(ask, wrap, text, oid) {
    wrap.dataset.answered = '1';
    wrap.querySelectorAll('.choice').forEach((c) => {
      c.classList.toggle('picked', c.dataset.oid === oid);
      c.classList.toggle('dim', c.dataset.oid !== oid);
      c.disabled = true;
    });
    fossilize(text, ask.title);
    pendingAsk = null;
    holdWriteline();
    sendTurn(`[card] ${ask.title} → ${oid ? text : `(custom) ${text}`}`);
    nudgeScroll();
  }

  // gate-2 R6: an ask that arrived while the C3 walk held the page renders on handback.
  function renderPendingAsk() { if (pendingAsk) renderAsk(pendingAsk); }

  // ── fossilized answers: the human is the serif (§4.1.3) ─────────────────
  function fossilize(text, q, rewritten) {
    const a = document.createElement('div');
    a.className = 'answer';
    if (q) a.dataset.q = q;
    a.textContent = text;              // the brass dash is CSS ::before
    if (rewritten) {
      const chip = document.createElement('span');
      chip.className = 'redone';
      chip.textContent = 'rewritten ↺';
      a.appendChild(chip);             // revision is part of the record (§2)
    }
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'rewrite';
    btn.textContent = '↺ rewrite';
    btn.addEventListener('click', () => beginRewrite(a));
    a.appendChild(btn);
    ((open && open.bodyEl) || $('#dz-live')).appendChild(a);
    return a;
  }

  // ── D1b: rewrite ⟲ (spec §5) — one in flight at a time ──────────────────
  let rw = null;
  let lastVerbFossil = null;   // the re-fossilized answer of the in-flight rewrite —
                               // marked "unsent" if that turn errors (gate-2 I8)

  function beginRewrite(ans) {
    if (rw || pendingTarget || busy) return;  // finish the open revision — and never
                                              // steal an in-flight turn's settle (I1)
    const sec = ans.closest('.dz-sec');
    const rec = chapters.find((c) => c.el === sec);
    if (!rec) return;
    const later = chapters.filter((c) => c.n > rec.n);
    later.forEach((c) => c.el.classList.add('stale'));
    document.querySelectorAll('#dz-rail .node').forEach((n) => {
      if (later.some((c) => c.phase === n.dataset.phase)) n.classList.add('stale');
    });
    const note = document.createElement('div');
    note.className = 'stale-note';
    note.textContent = `⟲ rewriting §${String(rec.n).padStart(2, '0')}` +
      ' — the architect will reconsider everything below';
    sec.after(note);
    // choice sections reopen their cards, re-choosable
    const grp = ans.closest('.dz-ask');
    if (grp) grp.querySelectorAll('.choice').forEach((c) => {
      c.disabled = false;
      c.classList.remove('dim');
    });
    // the fossil melts back into a writing line, pre-filled with the old words
    const old = (ans.firstChild && ans.firstChild.textContent || '').trim();
    const q = ans.dataset.q || '';
    const wl = document.createElement('form');
    wl.className = 'writeline';
    wl.innerHTML = '<span class="bar"></span><input autocomplete="off">';
    const inp = wl.querySelector('input');
    inp.value = old;
    ans.replaceWith(wl);
    inp.focus(); inp.select();
    holdWriteline();                          // the rewrite holds the baton
    rw = {
      rec, grp, note, later, wl, q, old,
      finish(text) {
        if (busy) return;    // gate-2 I1: a foreign turn queued between melt and submit
                             // must not have its settle stolen by this override —
                             // press Enter again once that turn lands (verbs-inert rule)
        const marker = document.createElement('div');
        this.wl.replaceWith(marker);
        lastVerbFossil = fossilAt(marker, text, this.q);   // re-fossilize in place, with
        marker.remove();                                   // the chip; remembered for I8
        this.note.remove();
        if (this.grp) {
          this.grp.querySelectorAll('.choice').forEach((c) => {
            const label = c.querySelector('b') ? c.querySelector('b').textContent : '';
            c.disabled = true;
            c.classList.toggle('picked', label === text);
            c.classList.toggle('dim', label !== text);
          });
        }
        // §5 pending-target override: the NEXT done beat routes to this chapter,
        // regardless of the emitted title, consuming exactly one beat.
        pendingTarget = { rec: this.rec, mode: 'append' };
        const later = this.later, n = this.rec.n;
        rwSettle = () => {
          lastVerbFossil = null;               // the rewrite landed — nothing to un-send (I8)
          later.forEach((c) => {
            c.el.classList.remove('stale');
            // honest scope (§5): downstream prose is NOT rewritten — it keeps its
            // text with a quiet mark until the participant regenerates it (⟳)
            if (c.bodyEl.querySelector('.dz-prose') && !c.bodyEl.querySelector('.dz-stale-mark')) {
              const m = document.createElement('div');
              m.className = 'dz-stale-mark';
              m.textContent = `written before your rewrite of §${String(n).padStart(2, '0')}` +
                ' — ⟳ regenerate to refresh';
              c.bodyEl.prepend(m);
            }
            // deterministic card re-settle: a still-unanswered downstream ask folds
            c.bodyEl.querySelectorAll('.dz-ask:not([data-answered])').forEach((w) => {
              w.dataset.answered = 'folded';
              w.querySelectorAll('.choice').forEach((x) => { x.disabled = true; x.classList.add('dim'); });
            });
          });
          document.querySelectorAll('#dz-rail .node.stale').forEach((x) => x.classList.remove('stale'));
        };
        sendTurn(`[studio event] rewrite — question: "${this.q}"` +
          ` — previous answer: "${this.old}" — new answer: "${text}"`);
        rw = null;
      },
    };
    inp.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' && inp.value.trim()) { ev.preventDefault(); rw.finish(inp.value.trim()); }
    });
  }

  // build a re-fossilized answer (with the rewritten chip) at a placeholder position
  function fossilAt(placeholder, text, q) {
    const host = placeholder.parentNode;
    const before = placeholder.nextSibling;
    const saveOpen = open;
    open = { bodyEl: host };            // fossilize appends to open — retarget briefly
    const a = fossilize(text, q, true);
    open = saveOpen;
    host.insertBefore(a, before);
    return a;
  }

  // re-choosing during a rewrite: a delegated handler (the per-card listeners are
  // guarded by data-answered and stay inert on reopened cards)
  document.addEventListener('click', (e) => {
    const ch = e.target.closest('.choice');
    if (!ch || !rw || !rw.grp || !rw.grp.contains(ch)) return;
    const label = ch.querySelector('b') ? ch.querySelector('b').textContent : '';
    if (label) rw.finish(label);
  });

  // gate-2 I8: an error on a VERB turn must not leave three-way incoherence — the
  // deferred re-settle is cancelled (it would otherwise fire on a LATER unrelated
  // beat, for a rewrite the agent never received), the un-received fossil says so
  // (its existing ↺ button IS the retry affordance — clicking it melts the answer
  // back into the line and re-sends), ⟳ shimmer and stale dressings come off.
  // Task 9's onError already clears pendingTarget.
  function verbErrorRecover() {
    if (rwSettle) {
      rwSettle = null;
      if (lastVerbFossil && !lastVerbFossil.querySelector('.unsent')) {
        const chip = document.createElement('span');
        chip.className = 'redone unsent';
        chip.textContent = 'unsent — ↺ retry';
        lastVerbFossil.appendChild(chip);
      }
    }
    lastVerbFossil = null;
    document.querySelectorAll('.dz-sec.dz-regenerating').forEach((s) => s.classList.remove('dz-regenerating'));
    document.querySelectorAll('.dz-sec.stale').forEach((s) => s.classList.remove('stale'));
    document.querySelectorAll('#dz-rail .node.stale').forEach((n) => n.classList.remove('stale'));
    document.querySelectorAll('.stale-note').forEach((n) => n.remove());
  }

  // ── the writing line — the document's next line ─────────────────────────
  function armWriteline(ask, hot) {
    if (hot && window.onboardingActive) hot = false;   // the C3 walk holds the baton
    const wl = $('#dz-writeline');
    const inp = $('#dz-input');
    wl.classList.toggle('held', !hot);
    inp.disabled = !hot;
    inp.placeholder = ask ? 'or write your own…' : 'write your line…';
    if (hot && !replaying) inp.focus({ preventScroll: true });
  }
  function holdWriteline() { armWriteline(pendingAsk, false); }

  $('#dz-writeline').addEventListener('submit', (e) => {
    e.preventDefault();
    const inp = $('#dz-input');
    const v = inp.value.trim();
    if (!v || inp.disabled) return;
    inp.value = '';
    if (pendingAsk && open) {
      const wrap = open.bodyEl.querySelector(
        `.dz-ask[data-ask-id="${CSS.escape(pendingAsk.id)}"]:not([data-answered])`);
      if (wrap) { answerAsk(pendingAsk, wrap, v, null); return; }
    }
    fossilize(v);
    holdWriteline();
    sendTurn(v);
    nudgeScroll();
  });

  // ── D3: intake as the opening chapter (§7.3 — zero backend change) ──────
  async function post(url, body) {
    const r = await fetch(url, { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
    return r.json();
  }

  function readFileB64(file) {
    return new Promise((res, rej) => {
      const fr = new FileReader();
      fr.onload = () => res(String(fr.result).split(',')[1] || '');
      fr.onerror = rej;
      fr.readAsDataURL(file);
    });
  }

  // gate-2 S3: a reload mid-intake resumes the WALK where the server's state file says
  // it stopped — the beats replay already restored the document and the session, so
  // no new session and no re-seed (intake() only creates a session at the name step).
  async function resumeIntake(state) {
    await getCatalog();
    if (!state || !state.name) return intake(state || {});   // name never landed — from the top
    window.onboardingActive = true;
    if (!open) newSection({ title: 'Welcome', phase: 'welcome' });
    if (!state.second_brain) { materialsStep(); return; }    // materials/home still open
    return completeIntake();            // everything chosen — finish the distill hand-off
  }

  async function intake(state) {
    await getCatalog();
    window.onboardingActive = true;     // suppress chat-skin paints; dossier owns the page
    const rec = newSection({ title: 'Welcome', phase: 'welcome' });
    rec.bodyEl.innerHTML = `
      <p class="dz-prose">Before anything else — who are you? Your chief of staff should
      know its owner by name.</p>
      <form class="dz-intake-name"><input id="dz-ob-name" type="text" maxlength="60"
        placeholder="your name" autocomplete="off" value="${esc((state && state.name) || '')}">
        <button type="submit">→</button></form>`;
    updateRail();
    const form = rec.bodyEl.querySelector('.dz-intake-name');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const inp = $('#dz-ob-name');
      const name = inp.value.trim();
      if (!name || inp.disabled) return;
      inp.disabled = true;
      const out = await post('/api/onboarding/name', { name });
      if (!out.ok) { alert(out.message); inp.disabled = false; return; }
      form.remove();
      fossilize(name, 'What should your chief of staff call you?');
      await window.startWorkshopSession('Begin onboarding.');   // agent greets by name
      materialsStep();
    });
  }

  function materialsStep() {
    const host = (open || newSection({ title: 'Welcome', phase: 'welcome' })).bodyEl;
    const registered = [];
    const wrap = document.createElement('div');
    wrap.className = 'dz-intake';
    wrap.innerHTML = `
      <div class="dz-drop" tabindex="0">⤓ drop your CV, LinkedIn screenshots, anything you've written
        <small>registered locally — nothing leaves your machine</small></div>
      <input type="file" class="dz-file-input" multiple hidden>
      <div class="dz-chips"></div>
      <label class="dz-field">or link a folder by path
        <input type="text" class="dz-folder" placeholder="e.g. ~/notes"></label>
      <div class="dz-intake-foot">
        <button type="button" class="dz-ob-skip">skip for now</button>
        <button type="button" class="dz-ob-go">That's everything →</button>
      </div>`;
    host.appendChild(wrap);
    const drop = wrap.querySelector('.dz-drop');
    const fileInput = wrap.querySelector('.dz-file-input');
    const chips = wrap.querySelector('.dz-chips');
    const addChip = (label, ok) => {
      const c = document.createElement('span');
      c.className = 'dz-mchip' + (ok ? ' ok' : '');
      c.textContent = (ok ? '✓ ' : '') + label;
      chips.appendChild(c);
    };
    async function takeFiles(files) {
      const names = [];
      for (const f of files) {
        addChip(f.name, false);
        const out = await post('/api/onboarding/materials',
          { file: { name: f.name, b64: await readFileB64(f) } });
        chips.lastChild.remove();
        addChip(f.name, !!out.ok);
        if (out.ok) { names.push(f.name); registered.push(f.name); }
        else alert(out.message);
      }
      if (names.length) window.queueSend(`[studio event] materials registered: ${names.join(', ')}`);
    }
    drop.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => { takeFiles([...e.target.files]); e.target.value = ''; });
    drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('over'));
    drop.addEventListener('drop', (e) => {
      e.preventDefault(); drop.classList.remove('over');
      takeFiles([...e.dataTransfer.files]);
    });
    const folder = wrap.querySelector('.dz-folder');
    folder.addEventListener('keydown', async (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      const out = await post('/api/onboarding/materials', { folder: folder.value.trim() });
      if (!out.ok) { alert(out.message); return; }
      addChip(folder.value.trim(), true); registered.push(folder.value.trim());
      window.queueSend(`[studio event] linked folder: ${folder.value.trim()}`);
      folder.value = '';
    });
    let answered = false;
    const finishMaterials = async (skipped) => {
      if (answered) return; answered = true;
      wrap.querySelectorAll('button').forEach((b) => { b.disabled = true; });
      if (skipped) await window.queueSend('[studio event] participant skipped sharing materials');
      else await post('/api/onboarding/materials/done', {});    // distiller starts now
      wrap.replaceWith(Object.assign(document.createElement('div'),
        { className: 'dz-receipt', textContent: registered.length ? `${registered.length} shared ✓` : 'materials skipped' }));
      pathStep();
    };
    wrap.querySelector('.dz-ob-skip').addEventListener('click', () => finishMaterials(true));
    wrap.querySelector('.dz-ob-go').addEventListener('click', () => finishMaterials(false));
  }

  function pathStep() {
    const host = (open || newSection({ title: 'Welcome', phase: 'welcome' })).bodyEl;
    const wrap = document.createElement('div');
    wrap.className = 'dz-intake';
    wrap.innerHTML = `
      <label class="dz-field">Where should its memory live? One folder you own, plain
        files — everything it learns about you lives here.
        <input type="text" class="dz-path" value="~/second-brain"></label>
      <div class="dz-intake-foot">
        <button type="button" class="dz-ob-skip">skip for now</button>
        <button type="button" class="dz-ob-go">This is home →</button>
      </div>`;
    host.appendChild(wrap);
    let answered = false;
    const finish = async (skipped) => {
      if (answered) return; answered = true;
      wrap.querySelectorAll('button').forEach((b) => { b.disabled = true; });
      const path = skipped ? '~/second-brain'
        : (wrap.querySelector('.dz-path').value.trim() || '~/second-brain');
      const out = await post('/api/onboarding/second-brain', { path });
      if (!out.ok && !skipped) {
        alert(out.message);
        wrap.remove();
        return pathStep();               // fresh fields — same retry shape as C3
      }
      if (skipped) await window.queueSend('[studio event] participant skipped choosing — defaulted to ~/second-brain');
      const shown = out.ok ? (out.second_brain || path) : path;
      wrap.replaceWith(Object.assign(document.createElement('div'),
        { className: 'dz-receipt', textContent: `home chosen ✓ ${shown}` }));
      completeIntake();
    };
    wrap.querySelector('.dz-ob-skip').addEventListener('click', () => finish(true));
    wrap.querySelector('.dz-ob-go').addEventListener('click', () => finish(false));
  }

  async function completeIntake() {
    // Stream the distill, hand the profile to the live agent — same shape as C3's
    // completeStep, ending in the interview, never a stuck page (try/finally).
    try {
      const r = await fetch('/api/onboarding/complete', { method: 'POST' });
      const reader = r.body.getReader(); const dec = new TextDecoder();
      let buf = '', profile = '', distilled = false;
      while (true) {
        const { value, done } = await reader.read(); if (done) break;
        buf += dec.decode(value, { stream: true });
        let i; while ((i = buf.indexOf('\n\n')) >= 0) {
          const line = buf.slice(0, i).replace(/^data: /, ''); buf = buf.slice(i + 2);
          if (!line) continue;
          const ev = JSON.parse(line);
          if (ev.type === 'profile') { profile = ev.text; distilled = !!ev.distilled; }
          if (ev.type === 'error') { onError(ev.message); return; }
        }
      }
      const state = await (await fetch('/api/onboarding')).json();
      const note = distilled ? 'Distilled profile:' : 'Materials registered but not yet distilled. Stub profile:';
      await window.queueSend(`[studio event] second brain created at ${state.second_brain}. ${note}\n${profile}`);
    } catch (e) {
      console.error('dossier intake complete failed', e);   // never strand the page
    } finally {
      window.onboardingActive = false;
      renderPendingAsk();                   // an ask parked mid-walk renders now (gate-2 R6)
      armWriteline(pendingAsk, true);       // the interview is live in the same document
    }
  }

  // ── the journey rail — derived, never stored (§4.2) ─────────────────────
  function buildRail() {
    $('#dz-rail').innerHTML = '<i id="dz-railfill"></i>' + PHASES.map((p, i) =>
      `<div class="node" data-phase="${p}" style="top:${6 + i * 14.5}%"><b></b><span>${p}</span></div>`
    ).join('');
    document.querySelectorAll('#dz-rail .node').forEach((n) => n.addEventListener('click', () => {
      if (!n.classList.contains('done') && !n.classList.contains('now')) return;
      const sec = document.querySelector(`.dz-sec[data-phase="${n.dataset.phase}"]`);
      if (sec) sec.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }));
  }

  function updateRail() {
    const seen = chapters.map((c) => PHASES.indexOf(c.phase)).filter((i) => i >= 0);
    const cur = open ? PHASES.indexOf(open.phase) : -1;
    document.querySelectorAll('#dz-rail .node').forEach((n) => {
      const i = PHASES.indexOf(n.dataset.phase);
      n.classList.remove('done', 'now');   // .stale is owned by the D1b rewrite flow
      if (seen.some((s) => s > i)) n.classList.add('done');      // a later phase was seen
      else if (i === cur) n.classList.add('now');
    });
    const fill = $('#dz-railfill');
    if (fill && cur >= 0) fill.style.height = (6 + cur * 14.5) + '%';
  }

  // follow the live edge only when the reader is already near it (scrollytell-safe)
  function nudgeScroll() {
    const nearBottom = window.innerHeight + window.scrollY > document.body.scrollHeight - 260;
    if (nearBottom) window.scrollTo({ top: document.body.scrollHeight, behavior: 'auto' });
  }

  window.dossier = { activate, tryReplay, onToken, onError, onDone, renderPendingAsk,
                     intake, resumeIntake };
})();
