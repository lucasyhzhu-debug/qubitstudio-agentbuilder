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
    armWriteline(pendingAsk, true);
    nudgeScroll();
  }

  // ── the settle: one done event = one beat (§4.1) ────────────────────────
  function onDone(ev, quiet) {
    busy = false;
    const studio = (ev && ev.studio) || lastStudio || {};
    const rec = settle(studio.chapter);
    if (studio.chapter && studio.chapter.blocks && studio.chapter.blocks.length) {
      renderBlocks(rec, studio.chapter.blocks);   // D1a: parser validates, renderer renders none (§3.2)
    }
    diffPicks(studio.picks || []);
    pendingAsk = studio.ask || null;
    // gate-2 R6: ONE hot surface — while the C3 walk holds the page the ask parks in
    // pendingAsk; renderPendingAsk renders it on handback (Task 10's baton hook).
    if (studio.ask && !quiet && !window.onboardingActive) renderAsk(studio.ask);
    lastStudio = studio;
    if (rwSettle) { rwSettle(); rwSettle = null; }   // D1b: honest re-settle after a rewrite beat
    if (!quiet) armWriteline(pendingAsk, true);
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
        target.rec.bodyEl.querySelectorAll('.dz-prose, .dz-error, .dz-stale-mark')
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
        <h2>${esc(ch.title)}</h2><span class="why">${esc(ch.phase)}</span></div>
      <div class="dz-body"></div>`;
    $('#dz-chapters').appendChild(sec);
    const rec = { n, title: ch.title, phase: ch.phase, el: sec,
                  bodyEl: sec.querySelector('.dz-body') };
    chapters.push(rec);
    open = rec;
    return rec;
  }

  // D2 renders the typed vocabulary; D1a accepts-and-ignores (§3.2).
  function renderBlocks(rec, blocks) {}

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
  function fossilize(text, q) {
    const a = document.createElement('div');
    a.className = 'answer';
    if (q) a.dataset.q = q;
    a.textContent = text;              // the brass dash is CSS ::before
    ((open && open.bodyEl) || $('#dz-live')).appendChild(a);
    return a;
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

  window.dossier = { activate, tryReplay, onToken, onError, onDone, renderPendingAsk };
})();
