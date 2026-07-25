---
name: Memory pins inherit the session cwd's project scope (home-cwd orphan trap)
description: A pin's governance scope is a side effect of the session's cwd, not of intent. A session running from ~ (home) writes pins to ~/.claude/projects/-Users-blakechasteen/memory/, NOT the mythrl-dev governed scope — silently orphaning them (no MEMORY.md/CATALOG index, no attestation, no memory-agent signing; home dir isn't even a git repo). HoloLoom indexes session .jsonl across ALL scopes, so search still surfaces the originating turns, masking the gap. Proven 2026-06-19 — reference_hermes.md "looked deleted" from mythrl-dev but was stranded in the home scope (authored 2026-04-21 from a home cwd).
type: feedback
originSessionId: 2026-06-19__3933fd38 — Hermes corpus trace; reference_hermes.md looked missing from mythrl-dev, found stranded in the home (~) scope and migrated this session
interpreted_by: claude-opus-4-8
---

**The trap.** Claude Code derives the memory directory from the session's cwd:
`~/.claude/projects/<cwd-slug>/memory/`. So a pin's **governance scope is a side
effect of where the session was launched**, not of intent. A session run from `~`
writes into `-Users-blakechasteen/memory/`; a session from `~/mythrl-dev` (or
below) writes into `-Users-blakechasteen-mythrl-dev/memory/` — the governed canon
scope this repo's CLAUDE.md, MEMORY.md/`catalog/CATALOG.md` index, attestation
discipline, and memory-agent SSH-signing all operate over.

**Why it bites.** A pin authored from the wrong cwd is silently orphaned:
- not in mythrl-dev's `MEMORY.md` / `catalog/CATALOG.md` index → never loaded into sessions;
- outside the top-of-canon / multi-session attestation disciplines;
- not memory-agent-signed (the home dir isn't even a git repo);
- yet **still discoverable** — HoloLoom's session indexer reads
  `~/.claude/projects/*.jsonl` across ALL scopes, so `hololoom_search
  corpus=sessions` surfaces the originating turns. The pin *looks* present in
  canon when it isn't. That masking is what makes it a trap rather than an
  obvious miss.

**Discovery (2026-06-19, sid8 3933fd38).** `reference_hermes.md` showed up in
session-turn search, but `cat` from mythrl-dev returned no-such-file. Pickaxe over
the mythrl-dev memory git history (`git log --all -S 'reference_hermes'`) returned
zero hits — never in this scope. `find ~/.claude -iname '*hermes*'` located it in
the home scope, authored 2026-04-21 by a home-cwd session. See [[reference_hermes]].

**Why:** governance scope silently follows cwd, and cross-scope search hides the
orphaning — so a pin can be ungoverned and unsigned while looking canonical.

**How to apply:**
- **Before writing a pin**, confirm cwd resolves to the governed scope: the target
  dir must be `…/-Users-blakechasteen-mythrl-dev/memory/`. Cheap check: `pwd`
  should be under `~/mythrl-dev`. On `main` from a home cwd, your pins will strand.
- **If a pin "looks deleted"/missing** from mythrl-dev, don't assume removal.
  Pickaxe first: `git log --all -S '<slug>'` in the memory dir — zero hits = never
  in this scope (check the home scope), nonzero = actually removed (recover from
  history). Then `find ~/.claude -iname '*<slug>*'`.
- **To rescue a stranded pin:** migrate into the governed scope via direct Bash
  write (per [[feedback_memory_edit_frontmatter_normalizer]]), normalize
  frontmatter (add `interpreted_by`, a governed `originSessionId`), parse-verify,
  index in `MEMORY.md` (spine) or `catalog/CATALOG.md` (low-centrality), and leave
  a redirect tombstone in the home original (home dir isn't git-tracked, so a stub
  honors [[feedback_archive_not_delete]] better than rm).

**Read with:**
- [[feedback_memory_edit_frontmatter_normalizer]] — the write-mechanics discipline migration must follow.
- [[feedback_memory_hook_attributes_committer_not_author]] — the governed scope's commit/provenance model the home scope lacks entirely.
- [[feedback_archive_not_delete]] — why tombstone-not-rm for the stranded original.
- [[reference_hermes]] — the discovery case.
