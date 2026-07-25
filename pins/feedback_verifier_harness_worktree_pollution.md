---
name: feedback_verifier_harness_worktree_pollution
description: Cross-instance verification subagents that EXECUTE a git-committing harness (e.g. ralph) can pollute the orchestrator's worktree — committing junk to its branch + dropping stray files in the worktree root. Sanity-check + reset git state before the clean commit; tell verifiers to copy OUTSIDE the parent repo.
metadata:
  type: feedback
interpreted_by: claude-opus-4-8
originSessionId: 2026-06-02__b8de3457 — ralph/autoresearcher sandbox-exec backstop build + 2-round cross-instance verify
---

When you fan out cross-instance verifiers (a Workflow of attacker subagents) that
**run a harness which itself does git operations** — ralph's loop `git init`s a
workspace and `commit`s every iteration — the verifiers can mutate the
*orchestrator's own worktree*, not just their intended `/tmp` copies. Observed
2026-06-02: after a 9-agent verification of the ralph sandbox, the worktree
branch had **13 junk `ralph: iter 1` commits** on top of its base and a pile of
stray dirs/files at the worktree root (`_isol_work/`, `_isol_tmp/`, `undefined/`,
`main.py`, `markerfb.txt`, `_verify_findings/`). Some attacker had run a ralph
copy whose paths resolved into the worktree and/or `git add -A && git commit`'d
there. My real work was still intact as **uncommitted working-tree edits**, but a
naive `git add -A && commit` would have shipped all the junk to `main`.

**Why:** subagents get a cwd (often the parent worktree) and full Bash; "copy to
/tmp first" in the prompt is a request, not a sandbox. A harness that commits
(ralph) turns a careless verifier into a committer on *your* branch. This is the
flip side of `[[feedback_verify_execution_not_bytes]]` — executing agent code is
powerful precisely because it has real effects, and those effects don't respect
your worktree boundary unless something enforces it.

**How to apply:**
1. **Before the clean commit, audit git state, don't trust it.** `git log --oneline base..HEAD`
   and `git status --porcelain`. If verifiers committed junk, `git reset <base>`
   (mixed — keeps your working-tree edits), `rm -rf` the stray artifacts, then
   `git add` *exactly* your intended files (list them explicitly; never `-A`),
   and re-verify the staged set before commit.
2. **Verify your real files still hold your final content** (grep markers): a
   verifier's `git reset/checkout` could have reverted them.
3. **Tell verifiers to copy the harness OUTSIDE the parent repo** (a true
   `mktemp -d /tmp/...`, not a path under the worktree) and never run git in the
   parent. Better: run them with `isolation: 'worktree'` so they physically
   cannot reach your tree.
4. The actual fix being verified (a `sandbox-exec` write-jail) would also contain
   this — verifiers run under the same OS confinement they're testing. Until then,
   the audit-and-reset above is the floor.

Sibling to `[[feedback_verify_across_instances]]` and `[[feedback_check_main_tip_before_building]]`
(both about the mechanics of multi-instance work); the merge half is the
shared-worktree hazard in `[[project_handoff_archive_discriminator_collision]]`.
