// The launch chooser — the studio's front door. app.js calls window.chooser.show() on a
// fresh launch (no ?door=/?mode=/?ui= and no session to resume). Each door reloads with a
// ?door=… param so start() re-runs cleanly on the chosen path:
//   cos   → Door A: the guided Chief-of-Staff workshop (unchanged)
//   build → Door B: the general "build any agent" architect journey
//   skill → Door C: a focused single-skill builder (constrained architect journey)
(function () {
  const DOORS = [
    { door: 'cos', badge: 'guided', primary: true, title: 'Chief of Staff',
      desc: 'The guided workshop — build a personal chief-of-staff agent on a proven substrate: '
        + 'briefing, scheduling, CRM, inbox drain and more.', go: 'Start the workshop ▸' },
    { door: 'build', badge: 'open-ended', title: 'Build any agent',
      desc: 'Describe any agent you want. The architect designs it — skills, tools, memory, '
        + 'routines — and builds it into an installable plugin.', go: 'Start from scratch ▸' },
    { door: 'skill', badge: 'focused', title: 'Build a skill',
      desc: 'Author one standalone skill you can drop into any Claude Code agent. Quick, focused, '
        + 'single-purpose.', go: 'Build a skill ▸' },
  ];

  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  function show() {
    const el = document.getElementById('chooser');
    if (!el) return;
    el.innerHTML = `
      <div class="ch-wrap">
        <div class="ch-eyebrow">Qubit Agent Studio</div>
        <h1 class="ch-h1">What do you want to build?</h1>
        <p class="ch-lede">Pick a starting point. You can always come back and build another.</p>
        <div class="ch-doors">
          ${DOORS.map((d) => `
            <button type="button" class="ch-door ${d.primary ? 'ch-primary' : ''}" data-door="${esc(d.door)}">
              <span class="ch-badge">${esc(d.badge)}</span>
              <h3>${esc(d.title)}</h3>
              <p>${esc(d.desc)}</p>
              <span class="ch-go">${esc(d.go)}</span>
            </button>`).join('')}
        </div>
      </div>`;
    el.hidden = false;
    el.classList.add('on');
    el.querySelectorAll('.ch-door').forEach((b) => {
      // A reload with the door fixed re-runs start() cleanly; the param persists across
      // reloads so a mid-journey refresh resumes instead of returning here.
      b.addEventListener('click', () => { location.search = '?door=' + b.dataset.door; });
    });
  }

  window.chooser = { show };
})();
