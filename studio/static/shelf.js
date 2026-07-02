/* ── Skill Shelf ──────────────────────────────────────────────────────────
   The shop's back room, rendered from /api/catalog. Participants build the
   locked baseline, then add à la carte skills; "Build my agent" hands the
   picks + a name straight to window.composeAgent (app.js), which drives
   /api/compose through the shared build panel. Everything here is
   data-driven — edit catalog.json to change the shelf. */
(function () {
  const sel = (s) => document.querySelector(s);
  const selected = new Map();   // id -> { it, origin: 'user' | 'agent' }
  let catalog = null;

  const btn = sel('#shelfbtn');
  const drawer = sel('#shelf-drawer');
  const backdrop = sel('#shelf-backdrop');

  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
  const tierClass = (t) => t === 'free' ? 't-free' : t === 'one' ? 't-one' : 't-many';

  function tag(cost) {
    cost = cost || {};
    return `<span class="price-tag ${tierClass(cost.tier)}"><i></i>${esc(cost.label || '')}</span>`;
  }

  function baselineCard(it) {
    return `<div class="shelf-card locked">
      <div class="sc-head"><span class="sc-name">${esc(it.name)}</span>${tag(it.cost)}</div>
      <p class="sc-what">${esc(it.what)}</p>
      <div class="sc-locked-note">&#128274; Included — everyone builds this</div>
    </div>`;
  }

  function shelfCard(it) {
    const v = selected.get(it.id);
    const on = !!v;
    const rec = v && v.origin === 'agent';
    return `<div class="shelf-card ${on ? 'on' : ''} ${rec ? 'recommended' : ''}" data-id="${esc(it.id)}">
      <div class="sc-head"><span class="sc-name">${esc(it.name)}</span>${tag(it.cost)}</div>
      ${rec ? '<div class="sc-rec">✓ recommended</div>' : ''}
      <p class="sc-what">${esc(it.what)}</p>
      ${it.deliverable ? `<div class="sc-deliv">makes <b>${esc(it.deliverable)}</b></div>` : ''}
      <button class="sc-add" data-id="${esc(it.id)}">${on ? '✓ Added' : 'Add to agent'}</button>
    </div>`;
  }

  function renderBody() {
    if (!catalog) return;
    const keep = sel('.shelf-foot .shelf-name')?.value;
    const b = catalog.baseline || { items: [] };
    const sh = catalog.shelf || { items: [] };
    sel('.shelf-body').innerHTML = `
      <div class="shelf-group">
        <h3>${esc(b.title || 'Baseline')}</h3>
        <p class="sub">${esc(b.subtitle || '')}</p>
        ${(b.items || []).map(baselineCard).join('')}
      </div>
      <div class="shelf-group">
        <h3>${esc(sh.title || 'On the shelf')}</h3>
        <p class="sub">${esc(sh.subtitle || '')}</p>
        ${(sh.items || []).map(shelfCard).join('')}
      </div>`;
    renderFoot();
    const nf = sel('.shelf-foot .shelf-name'); if (nf && keep) nf.value = keep;
    updateBtn();
  }

  function renderFoot() {
    const items = [...selected.values()].map((v) => v.it);
    const ints = [...new Set(items.flatMap((it) => it.requires || []))];
    const chips = ints.length
      ? ints.map((i) => `<span class="int-chip">${esc(i)}</span>`).join('')
      : '<span style="font-size:11px;color:var(--dim);font-family:var(--mono)">no integrations yet</span>';
    sel('.shelf-foot').innerHTML = `
      <div class="basket-line"><b>${items.length}</b> skill${items.length === 1 ? '' : 's'} on top of your baseline</div>
      <div class="basket-ints">${chips}</div>
      <input class="shelf-name" type="text" placeholder="Name your agent (e.g. my-cos)" maxlength="60">
      <button class="brief-btn" ${items.length ? '' : 'disabled'}>Build my agent &#9654;</button>`;
    const bb = sel('.shelf-foot .brief-btn');
    if (bb) bb.addEventListener('click', buildAgent);
  }

  function updateBtn() {
    btn.classList.toggle('has-picks', selected.size > 0);
    sel('#shelfbtn .count').textContent = selected.size;
  }

  function toggle(id) {
    const it = (catalog.shelf.items || []).find((x) => x.id === id);
    if (!it) return;
    if (selected.has(id)) selected.delete(id); else selected.set(id, { it, origin: 'user' });
    renderBody();  // re-render so on/recommended states stay truthful
  }

  function buildAgent() {
    if (!selected.size) return;
    if (typeof window.composeAgent !== 'function') {
      alert('The build panel isn’t ready yet — reload and try again.');
      return;
    }
    const nameField = sel('.shelf-foot .shelf-name');
    const name = (nameField && nameField.value.trim()) || window.prompt('Name your agent (used for the plugin folder):', '') || '';
    if (!name) return;
    window.composeAgent([...selected.keys()], name);
    close();
  }

  // Called by the Your-agent panel (app.js). Fills the drawer's name field if the
  // panel supplied one, then runs the same buildAgent() path.
  window.shelfBuild = function (name) {
    const f = sel('.shelf-foot .shelf-name');
    if (name && f && !f.value.trim()) f.value = name;
    buildAgent();
  };

  function open() {
    backdrop.hidden = false; drawer.hidden = false;
    requestAnimationFrame(() => { backdrop.classList.add('open'); drawer.classList.add('open'); });
  }
  function close() {
    backdrop.classList.remove('open'); drawer.classList.remove('open');
    const done = () => { backdrop.hidden = true; drawer.hidden = true; drawer.removeEventListener('transitionend', done); };
    drawer.addEventListener('transitionend', done);
    setTimeout(done, 350);  // fallback if transitionend doesn't fire (reduced motion)
  }

  // Chat→shelf sync (spec §4.4): the agent's studio block re-asserts ITS picks only.
  // User-added picks are never removed by a sync; agent picks no longer recommended drop.
  function shelfSync(studio) {
    if (!catalog || !studio) return;
    const picks = new Set(studio.picks || []);
    for (const [id, v] of [...selected]) {
      if (v.origin === 'agent' && !picks.has(id)) selected.delete(id);
    }
    for (const id of picks) {
      if (!selected.has(id)) {
        const it = (catalog.shelf.items || []).find((x) => x.id === id);
        if (it) selected.set(id, { it, origin: 'agent' });
      }
    }
    renderBody();
    const nameField = sel('.shelf-foot .shelf-name');
    if (studio.name && nameField && !nameField.value.trim()) nameField.value = studio.name;
  }
  window.shelfSync = shelfSync;

  async function init() {
    try {
      catalog = await (await fetch('/api/catalog')).json();
    } catch {
      catalog = { baseline: { items: [] }, shelf: { items: [] } };
    }
    renderBody();
  }

  btn.addEventListener('click', open);
  sel('.shelf-close').addEventListener('click', close);
  backdrop.addEventListener('click', close);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !drawer.hidden) close(); });
  drawer.addEventListener('click', (e) => {
    const add = e.target.closest('.sc-add');
    if (add) toggle(add.dataset.id);
  });

  init();
})();
