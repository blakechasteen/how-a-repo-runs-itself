---
name: feedback_subagents_write_in_primary_tree
description: Spawned sub-agents (Agent tool) run in the PRIMARY main checkout, not the spawning session's worktree — file-writing agents leave untracked debris in the shared tree that can abort your merge. A third worktree collision class.
metadata:
  type: feedback
originSessionId: 2026-06-21__0baea73c — passage-DPR multi-hop re-probe; a sonnet sub-agent recreated a harness in primary, aborting the merge
interpreted_by: claude-opus-4-8
---

Spawned sub-agents (the Agent tool) execute in the **primary `main` checkout**, NOT the worktree of the session that spawned them. Observed 2026-06-21 (sid8 0baea73c): a Sonnet sub-agent told to run `tools/_multihop_extprobe.py` — which existed only in the spawning session's worktree — couldn't find it in primary, **recreated its own copy there**, and that untracked file later aborted the parent's `git -C <primary> merge` with *"untracked working tree files would be overwritten by merge."*

**Why:** worktree-per-session isolates the SPAWNING session, but sub-agents don't inherit the worktree — they read/write the shared tree that every other live session (and your eventual merge) sees. This is a **third collision class** beyond the two in CLAUDE.md (namespace-collision `dc90a13`, merge-into-dirty-tree `ec63b05c`): *sub-agent writes pollute primary*. It also means a self-running agent's reported numbers can come from tooling it rebuilt in primary, not your reviewed code.

**How to apply:**
1. When spawning agents that might WRITE, confine them — instruct outputs to `/tmp` only, or keep the fan-out read-only. The legit win from fan-out is decorrelated authoring/verification, which is read-shaped ([[feedback_fan_out_only_when_write_independent]]).
2. Before merging a worktree branch, run `git -C <primary> status --short` and clear untracked agent debris — but **diff it first** ([[feedback_archive_not_delete]]): an untracked file may be another session's namespace collision, not your agent's. Preserve, don't blind-`rm`.
3. Treat a sub-agent's self-run results as unverified until you re-run its inputs through your own controlled harness ([[feedback_no_fabricated_results]], [[feedback_builder_cannot_self_verify]]).

Sibling to the worktree collision-class analysis in [[project_mast_self_audit_verdict]]; verify-before-trust kin of [[feedback_verify_across_instances]].
