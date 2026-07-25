---
name: feedback_memory_edit_frontmatter_normalizer
description: Edit/Write tool calls on memory/*.md can trigger the Claude Code auto-memory normalizer, which silently REWRITES pin frontmatter to a stub (name "", node_type memory, originSessionId = the EDITING session) — destroying name/description/interpreted_by/attestations and stamping false provenance. Author/repair via direct Bash write; parse-verify frontmatter after every memory edit. Proven 2026-06-11 (2x on one pin, same session).
metadata:
  type: feedback
interpreted_by: claude-fable-5
originSessionId: 2026-06-11__7397c3aa — garage-pin reframe + fresh-context attestation; the normalizer stubbed project_garage_phase.md twice mid-amendment
---

**The gotcha (proven 2026-06-11, session 7397c3aa, on `project_garage_phase.md` — twice).**
During a canon amendment, the harness's auto-memory normalizer rewrote the pin's entire
frontmatter to a stub — `name: ""` / `metadata.node_type: memory` / `originSessionId: <the
EDITING session's UUID>` — destroying the name, description, `interpreted_by`, the original
author's `originSessionId`, and the `attestations:` field *including a just-landed attestation
tuple*. Stamping the editing session over the real author is the same false-attribution class as
[[feedback_memory_hook_attributes_committer_not_author]], but harness-side and content-destroying.
Trigger correlation from the incident: both stubs landed within seconds-to-minutes of **Edit-tool**
writes to the file; a **direct Bash/python file write** of the same content bypassed the normalizer
and held. Blast radius verified before repair: `git log --all -S "node_type: memory"` found nothing
in history — working-tree only, one file; other pins untouched. Same incident also surfaced a YAML
trap: an unquoted frontmatter scalar containing `": "` (colon-space) breaks parsing — the original
description avoided it, an amendment introduced it, and only a mechanical parse caught it.

**Why:** Provenance and attestation frontmatter are the substrate's epistemic load-bearers
([[project_interpretation_tier]]; the memory-provenance discipline in CLAUDE.md). A harness-side
normalizer silently replacing them re-introduces AI-session false-attribution with no one intending
it — and the damage rides into canon via the memory Stop-hook commit if nobody looks. The stub is
also valid-looking YAML, so nothing downstream errors; only a field-presence check notices.

**How to apply:**
1. After ANY write to a `memory/*.md` pin, mechanically verify: frontmatter parses
   (`yaml.safe_load`) AND still carries `name` / `description` / `interpreted_by` /
   `originSessionId` (+ `attestations` where present). Five lines of python; do it in the same
   turn as the edit.
2. If stubbed (`name: ""` + `node_type: memory`), repair via a DIRECT file write (Bash/python heredoc),
   not Edit/Write — Edit re-triggered the normalizer in the proven instance; the Bash write held.
   Reconstruct from the memory repo's last hook commit (`git show <sha>:<file>`) plus your in-context
   edits; never re-type provenance fields from memory.
3. Keep `": "` out of unquoted frontmatter scalars (use an em-dash or quote the scalar).
4. Before session end, re-check every pin touched this session — the Stop hook commits whatever
   state is on disk, attributed to your session.

Siblings: [[feedback_memory_hook_attributes_committer_not_author]] (hook-side attribution),
[[feedback_no_fabricated_results]] (mechanical verify over trust), [[feedback_realtime_coediting]]
(external mid-session modification — but this modifier is a normalizer, not an author: its edits
are NOT authoritative and should be repaired).
