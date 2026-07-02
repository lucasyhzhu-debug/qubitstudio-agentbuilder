// The onboarding walk (onboarding-cards spec §5.4): fade-in welcome, then the live agent
// narrates on the left while the right rail runs files -> path cards. Every visible
// bubble is real model output; the UI only sends [studio event] messages (suppressed).
(function () {
  const $ = (s) => document.querySelector(s);
  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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

  function begin(state) {
    window.onboardingActive = true;
    $('#onboard-overlay').hidden = false;
    const nameInput = $('#ob-name-input');
    if (state && state.name) nameInput.value = state.name;
    nameInput.focus();
    // Persistent listener with a re-entrancy guard — `{once:true}` would brick the form
    // if the first submit had an empty name (review I3).
    $('#ob-name-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = nameInput.value.trim();
      if (!name || nameInput.disabled) return;
      nameInput.disabled = true;
      const out = await post('/api/onboarding/name', { name });
      if (!out.ok) { alert(out.message); nameInput.disabled = false; return; }
      welcome(name);
    });
  }

  function welcome(name) {
    $('#ob-name').hidden = true;
    const w = $('#ob-welcome');
    $('#ob-welcome-title').textContent = `Welcome, ${name}.`;   // textContent — no injection
    w.hidden = false;
    setTimeout(reveal, REDUCED ? 0 : 2200);
  }

  async function reveal() {
    const ov = $('#onboard-overlay');
    ov.classList.add('ob-slide-up');                            // one continuous motion
    setTimeout(() => { ov.hidden = true; }, REDUCED ? 0 : 650);
    // The walk owns #blueprint while onboardingActive gates the panel repaints; clear
    // the static empty-state div so cards don't render around it.
    const rail = $('#blueprint');
    rail.innerHTML = '';
    window.cards.mount(rail);
    window.cards.queue([{ eyebrow: 'mind-palace' }]);           // path step waits ghosted
    await window.startWorkshopSession('Begin onboarding.');     // agent greets by name
    filesStep();
  }

  function filesStep() {
    const registered = [];
    const el = window.cards.show({
      id: 'ob-files', producer: 'onboarding', kind: 'files',
      eyebrow: 'onboarding · know you', progress: { i: 1, n: 2 },
      title: 'Help me get to know you',
    }, async (a) => {
      if (a.skipped) await window.queueSend('[studio event] participant skipped sharing materials');
      else await post('/api/onboarding/materials/done', {});    // distiller starts now
      window.cards.fold('ob-files', registered.length ? `${registered.length} shared ✓` : 'skipped');
      pathStep();
    });

    const drop = el.querySelector('.card-drop');
    const fileInput = el.querySelector('.card-file-input');
    const chips = el.querySelector('.card-chips');
    const addChip = (label, ok) => {
      const c = document.createElement('span');
      c.className = 'chip' + (ok ? '' : ' pending');
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
    const folder = el.querySelector('.card-folder');
    folder.addEventListener('keydown', async (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      const out = await post('/api/onboarding/materials', { folder: folder.value.trim() });
      if (!out.ok) { alert(out.message); return; }
      addChip(folder.value.trim(), true); registered.push(folder.value.trim());
      window.queueSend(`[studio event] linked folder: ${folder.value.trim()}`);
      folder.value = '';
    });
  }

  function pathStep() {
    // The real card replaces its ghosted placeholder (cards.queue has no dequeue API).
    const ghost = document.querySelector('#blueprint .card.ghost');
    if (ghost) ghost.remove();
    window.cards.show({
      id: 'ob-path', producer: 'onboarding', kind: 'path',
      eyebrow: 'onboarding · mind-palace', progress: { i: 2, n: 2 },
      title: 'Where should its memory live?',
      why: 'One folder you own, plain files — everything it learns about you lives here.',
      default: '~/second-brain',
    }, async (a) => {
      if (a.skipped) {
        // Skip-all path (review I6): default location, stub profile — never stall.
        const out = await post('/api/onboarding/second-brain', { path: '~/second-brain' });
        if (!out.ok) {
          // Default home failed too — don't pretend it was chosen; proceed anyway,
          // completeStep's finally hands the UI back (final review I6b).
          window.cards.fold('ob-path', 'skipped');
          return completeStep();
        }
        await window.queueSend('[studio event] participant skipped choosing — defaulted to ~/second-brain');
      } else {
        const path = document.querySelector('.card[data-card-id="ob-path"] .card-path').value.trim();
        const out = await post('/api/onboarding/second-brain', { path: path || '~/second-brain' });
        if (!out.ok) {
          alert(out.message);
          window.cards.fold('ob-path', '✗ try again');   // fold the failed card first (review I4)
          return pathStep();                             // fresh card prepends — fold() targets it next
        }
      }
      window.cards.fold('ob-path', 'home chosen ✓');
      completeStep();
    });
  }

  async function completeStep() {
    // Stream the distill; then hand the profile to the live agent as an event.
    // try/finally (final review I6a): the handback ALWAYS runs — on fetch/SSE failure or
    // a preflight error the walk still ends into a normal interview, never a stuck
    // asleep composer.
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
          if (ev.type === 'error') { alert(ev.message); return; }   // finally still hands back
        }
      }
      const state = await (await fetch('/api/onboarding')).json();
      const note = distilled ? 'Distilled profile:' : 'Materials registered but not yet distilled. Stub profile:';
      await window.queueSend(`[studio event] second brain created at ${state.second_brain}. ${note}\n${profile}`);
    } catch (e) {
      console.error('onboarding complete failed', e);   // never strand the walk
    } finally {
      window.onboardingActive = false;
      await window.cards.morph('');                 // clear the rail — resolves AFTER the swap (review C1)
      if (typeof renderAgentPanel === 'function') renderAgentPanel(null);   // …hand back the panel
      window.cards.baton('composer');               // the interview is live
      // Replay an ask the walk suppressed mid-flight (final review I6c).
      if (window._pendingAsk && typeof window.renderAskCard === 'function') {
        window.renderAskCard(window._pendingAsk);
        window._pendingAsk = null;
      }
    }
  }

  window.onboardWalk = { begin };
})();
