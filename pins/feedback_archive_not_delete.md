---
name: Archive, don't delete — preserve for archaeology
description: When pruning code or docs the user calls "bloat," default to in-tree archive/ moves with git rename history, not deletion. They treat the codebase as a record of thinking.
type: feedback
originSessionId: c2e98b4f-e41f-466d-884b-1da3bda4a1e8
interpreted_by: claude-opus-4-7
---
When the user asks to clean up "bloat," "wads," "stale stuff," or
similar in their codebases, the default action is **move into an
in-tree `archive/` subtree**, not delete. Use `git mv` so rename
history is preserved and `git log --follow` keeps working.

**Why:** The user explicitly said after a Phase 1 HoloLoom cleanup
(May 2026): "i do want to keep this for future excavation
archaeology." They treat older code, abandoned plans, and superseded
docs as a record of thinking — useful for understanding how the
current system got its shape. Pre-reframe roadmaps and dead
orchestrator variants weren't junk to them; they were strata.

**How to apply:**
- For "bloat" / "wad" / "this is too much" requests, propose a
  quarantine layout (e.g. `archive/<topic>/`, `archive/_<era>/`)
  before any rm.
- Use `git mv` per-batch with descriptive commits so each category
  can be reverted independently.
- Always add an `archive/README.md` recording what moved, when, and
  why — that's the archaeology metadata.
- Don't delete empty dirs without checking — they may hold non-Python
  artifacts (configs, dashboards, JSON) the user wants to keep.
- Even when the user says "destroy" or "kill" something, confirm
  whether they mean delete-delete or move-to-archive before doing
  the irreversible thing.
