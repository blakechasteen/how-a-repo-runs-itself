---
name: Surface bloat early — don't make user threaten refactor
description: 'Watch for archaeological strata accumulating in projects and raise it proactively before the user has to call it out. Their May 2026 nudge: "dont make me threaten refactor again."'
type: feedback
originSessionId: c2e98b4f-e41f-466d-884b-1da3bda4a1e8
interpreted_by: claude-opus-4-7
---
When working in any of the user's projects, watch for accumulating
archaeology and surface it the moment it crosses into "wad" territory —
don't wait for the user to call it out.

**Why:** After the May 2026 HoloLoom 5-commit cleanup (90 dirs → 68
live, two front doors collapsed, five orchestrator variants → two,
~250KB stale strategy docs archived) the user said "dont make me
threaten refactor again." They want this kind of pruning to be
ongoing hygiene, not a periodic crisis pass.

**Specific signals to flag in the moment they show up:**

- Multiple files with `_variant`, `_v2`, `_refactored`, `_bandit`,
  `_recursive`, `_<adjective>` suffixes living next to a canonical
  one. After the second variant, raise it.
- Doc dates >3 months stale relative to neighboring code mtimes.
- Strategy/roadmap docs declaring "Vision Complete ✅" or "$X ARR" or
  "Ready to Build 🚀" that don't match what's actually running.
- Dirs untouched for >60 days while neighboring dirs get heavy
  edits — possible closed-set archaeology.
- Two API surfaces / two front-door classes / two MCP servers for
  the same logical role.
- Test files importing modules nobody else does.
- `__pycache__/`, `.venv/`, build artifacts checked into git.
- README/MASTER_INDEX/CLAUDE.md describing systems that don't match
  the code anymore.

**How to apply:**

- When I notice one of these mid-task, drop a one-liner in the
  current response: "Noticed N orchestrator variants — worth a Phase
  2 pass after this?" Don't lecture, don't bury it in a paragraph.
- Don't act unilaterally on cleanup beyond the immediate task —
  the user wants the offer, not the surprise. (Confirmation pattern
  from the May 2026 pass: I proposed Phase 1, they said "do it.")
- Default to in-tree archive/ moves, not deletion (see
  feedback_archive_not_delete.md).
- Keep the offer cheap: "want me to take a haircut at this?" One
  sentence. They'll tell me yes/no/later.
- If they say "later" or skip, don't re-raise the same observation
  next turn — they got it.
