// Guided card framework (onboarding-cards spec §3). One primitive, four producers:
// onboarding steps, the architect's asks, per-skill personalize (r1-B), connect keys.
// Motion vocabulary: rise / fold / baton / morph — all collapse under reduced motion.
(function () {
  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  let root = null;               // mount element (the right-panel rail)
  let batonFns = [];             // app.js registers composer sleep/wake here

  function mount(el) { root = el; root.classList.add('cards-rail'); }

  function baton(holder) { batonFns.forEach((fn) => fn(holder)); }
  function onBaton(fn) { batonFns.push(fn); }

  function bodyHtml(card) {
    if (card.kind === 'files') {
      return `<div class="card-drop" tabindex="0">⤓ drop files here
          <small>locations registered locally — nothing leaves your machine</small></div>
        <input type="file" class="card-file-input" multiple hidden>
        <div class="card-chips"></div>
        <label class="card-field">or link a folder by path
          <input type="text" class="card-folder" placeholder="e.g. ~/notes"></label>
        <div class="card-foot">
          ${card.skippable === false ? '' : '<button type="button" class="card-skip">skip for now</button>'}
          <button type="button" class="card-go">That's everything →</button>
        </div>`;
    }
    if (card.kind === 'path') {
      return `<label class="card-field">${esc(card.why || '')}
          <input type="text" class="card-path" value="${esc(card.default || '')}"></label>
        <div class="card-foot">
          ${card.skippable === false ? '' : '<button type="button" class="card-skip">skip for now</button>'}
          <button type="button" class="card-go">This is home →</button>
        </div>`;
    }
    // kind === 'question' (the visual AskUserQuestion). `keys` is reserved for the
    // connect slice — same shell, steps+paste+Test body (spec §3.1).
    const opts = (card.options || []).map((o) => `
      <div class="card-choice" data-oid="${esc(o.id)}" role="button" tabindex="0">
        <span class="card-key">${esc(o.id.toUpperCase())}</span>
        <span><b>${esc(o.label)}</b>${o.why ? `<i>${esc(o.why)}</i>` : ''}</span>
      </div>`).join('');
    return `${opts}
      <div class="card-orline">or in your own words</div>
      <textarea class="card-own" rows="2" placeholder="type your own answer…"></textarea>
      <div class="card-foot">
        ${card.skippable === false ? '' : '<button type="button" class="card-skip">skip</button>'}
        <button type="button" class="card-go" disabled>Answer →</button>
      </div>`;
  }

  function show(card, onAnswer) {
    if (!root) return;
    const el = document.createElement('div');
    el.className = 'card hot rise';
    el.dataset.cardId = card.id;
    el.innerHTML = `
      <div class="card-head"><span class="card-eyebrow">${esc(card.eyebrow || '')}</span>
        ${card.progress ? `<span class="card-prog">${card.progress.i} OF ${card.progress.n}</span>` : ''}</div>
      <h3>${esc(card.title || '')}</h3>
      ${card.kind === 'question' && card.why ? `<p class="card-why">${esc(card.why)}</p>` : ''}
      ${bodyHtml(card)}`;
    root.prepend(el);
    baton('card');

    const picked = new Set();
    const go = el.querySelector('.card-go');
    const own = el.querySelector('.card-own');
    let answered = false;   // double-click / Enter+click re-entrancy guard (final review C3)
    const answer = (a) => {
      if (answered) return;
      answered = true;
      el.querySelectorAll('.card-go, .card-skip').forEach((b) => { b.disabled = true; });
      onAnswer({ card_id: card.id, choices: [...picked],
      custom: own && own.value.trim() ? own.value.trim() : null,
      skipped: false, payload: null, ...a }); };

    el.querySelectorAll('.card-choice').forEach((c) => {
      const pick = () => {
        const oid = c.dataset.oid;
        if (!card.multi) { picked.clear(); el.querySelectorAll('.card-choice').forEach((x) => x.classList.remove('picked')); }
        if (picked.has(oid)) { picked.delete(oid); c.classList.remove('picked'); }
        else { picked.add(oid); c.classList.add('picked'); }
        if (go) go.disabled = picked.size === 0 && !(own && own.value.trim());
      };
      c.addEventListener('click', pick);
      c.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); } });
    });
    if (own && go) own.addEventListener('input', () => { go.disabled = picked.size === 0 && !own.value.trim(); });
    if (go) go.addEventListener('click', () => answer({}));
    const skip = el.querySelector('.card-skip');
    if (skip) skip.addEventListener('click', () => answer({ skipped: true, choices: [], custom: null }));
    return el;
  }

  function queue(cardsList) {
    if (!root) return;
    (cardsList || []).forEach((c) => {
      const el = document.createElement('div');
      el.className = 'card ghost';
      el.innerHTML = `<div class="card-head"><span class="card-eyebrow">${esc(c.eyebrow || '')}</span></div>`;
      root.appendChild(el);
    });
  }

  function fold(cardId, receipt) {
    if (!root) return;
    const el = root.querySelector(`.card[data-card-id="${CSS.escape(cardId)}"]`);
    if (!el) return;
    const text = String(receipt || '✓').slice(0, 60);  // length-capped receipt (review R3)
    el.classList.remove('hot');
    el.classList.add('folded');
    el.innerHTML = `<div class="card-receipt">${esc(text)}</div>`;
    delete el.dataset.cardId;   // folded cards must not shadow a future ask reusing the id (final review I5)
  }

  function morph(html) {
    // Resolves AFTER the swap — callers must await before repainting the same element
    // (review C1: a fire-and-forget timeout here would wipe whatever they paint next).
    return new Promise((res) => {
      if (!root) return res();
      const el = root;
      el.classList.add('morphing');
      setTimeout(() => {
        el.innerHTML = html;
        el.classList.remove('morphing', 'cards-rail');
        res();
      }, 220);
    });
  }

  window.cards = { mount, show, queue, fold, morph, baton, onBaton };
})();
