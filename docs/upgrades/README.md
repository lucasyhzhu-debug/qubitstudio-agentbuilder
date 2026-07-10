# Substrate upgrade packages

This directory is the **publication channel** for improvements made to the upstream personal
chief-of-staff (the private `Consulting-Agents` repo) that should flow into this repo's
placeholder-form substrate — and onward into participants' personalized agents.

## Why spec packages instead of file diffs

The substrate here is **scrubbed to placeholder form** and participants' copies are
**personalized** (names, vault paths, Linear workspaces, channel rosters all differ). A literal
file diff from the upstream repo would carry owner-specific text and would not apply cleanly to a
personalized tree. So upgrades ship as **spec requirement documents**: each describes the
*behavioral* change precisely enough for a Claude Code session (in this repo, or in a
participant's agent home) to interpret and apply to whatever the local skill text looks like.

## Package format

One markdown file per upstream release batch, named `YYYY-MM-DD-cos-vX.Y.Z-upgrade.md`, containing:

- **Provenance** — upstream version range, commit hashes, publication date.
- **One section per change**: What / Why (the incident or gap that motivated it) / Where (which
  skill, reference, or script) / Spec requirements (numbered, testable statements) / Acceptance
  check (how to verify the change landed).
- **Scrub notes** — any owner-specific values in the upstream change and their placeholder or
  fetch-it-yourself treatment (`{{LINEAR_TEAM_ID}}`, workspace-specific state ids, etc.).

## How to apply a package

In a Claude Code session in this repo (or a participant's agent home), point Claude at the
package file and ask it to apply the upgrade. Claude reads each spec requirement, finds the
corresponding place in the local (possibly personalized) skill text, and updates it — preserving
local personalization. Verify with the acceptance checks, then commit.

## How participants pull updates (automated)

Every agent the studio composes is stamped and self-updating, so participants get these packages
without touching this repo:

- The composer makes each `dist/<name>-cos/` home its **own git repo** and writes
  `.cos-update.json` recording the substrate `version` it was built from (the `SUBSTRATE_VERSION`
  anchor) plus the upstream coordinates (`upstream_repo`, `upstream_branch`, `packages_path`).
- Every home ships the **`cos-update`** skill (`chief-of-staff/skills/cos-update/`). When the owner
  says *"update me"*, it reads `.cos-update.json`, lists this directory via the GitHub contents API,
  applies every package **newer** than the home's version to the local personalized skills (same
  discipline as above), bumps the recorded version, and commits to the owner's repo. The owner's
  history and vault memory survive a studio re-compose.

**Maintainer contract:** when you publish a new package here, also bump
`chief-of-staff/SUBSTRATE_VERSION` to the package's version so freshly composed agents record the
right baseline. Package filenames must stay in the `YYYY-MM-DD-cos-vX.Y.Z-upgrade.md` form —
`cos-update` parses the `vX.Y.Z` from the name to decide what's newer.

## Rules

- Packages describe **shipped** upstream changes (a version that landed on the upstream `main`).
  In-flight work is at most trailed as "coming next" — never spec'd before it survives upstream
  review.
- No owner PII ever enters a package: names → `{{OWNER_NAME}}` / bare substrate anchor, emails →
  `you@example.com`, workspace ids → placeholders or a fetch instruction.
- Newest package supersedes older ones where they touch the same requirement; apply in date order
  when catching up across several.
