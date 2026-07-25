---
name: feedback_session_end_hook_best_effort
description: Claude Code's SessionEnd hook is BEST-EFFORT — docs say it "may not run" if Claude Code crashes or is killed, and it has an `other` catch-all reason (not a closed graceful-only set). Never hang must-run cleanup on it. SessionStart runs on every session. Lazy-create-at-use + inline-destroy + a scheduled sweep is the durable pattern.
metadata:
  type: feedback
interpreted_by: claude-opus-4-8
originSessionId: 2026-06-04__c569a4ce — diagnosing the session-key forward-secrecy leak (240 orphaned ephemeral keys)
---

Claude Code's **SessionStart** hook runs on every session, but **SessionEnd is
best-effort**. Per the official hooks docs (https://code.claude.com/docs/en/hooks,
re-verified 2026-06-04): *"SessionEnd hooks run on a best-effort basis: if Claude
Code crashes or is killed, they may not run,"* and *"Do not rely on SessionEnd
hooks for critical cleanup."* Its documented `reason` values are `clear`,
`resume`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, and
**`other`** ("session ended for any other reason") — the explicit `other`
catch-all means it is **not** a closed graceful-only set. The *documented*
non-firing conditions are exactly **crash and kill (SIGKILL)**; idle-timeout and
terminal-close are plausible but **not** documented — treat them as inference,
not doc fact.

So any invariant of the shape **"resource X is created at SessionStart and
destroyed at SessionEnd"** silently breaks for every non-graceful exit — which,
on a busy multi-session machine, is *most* sessions.

**Why:** the asymmetry is structural, not a config bug. The reliable-create /
unreliable-destroy pairing accumulates orphans monotonically. Concrete instance
that motivated this pin: the session-chain forward-secrecy leak — SessionStart
minted an ephemeral Ed25519 key for **every** session, but destruction hung on
the SessionEnd reaper, so **240 private keys** piled up on disk (the very
forward-secrecy breach identity-keys exist to prevent). See [[project_session_chain]]
and [[project_judgment_verify_needs_identity_keys]].

**How to apply:**
- Never put must-run cleanup (key destruction, lock release, temp removal,
  unwind) **only** in a SessionEnd hook.
- Prefer **lazy create-at-point-of-use + inline destroy**: create the resource
  exactly when first needed and tear it down in the same code path, so it
  exists only as briefly as possible and most sessions never create it at all.
  (The fix: mint the ephemeral key lazily inside `attest()` on a session's first
  memory write, destroy it inline — ~95% of sessions now mint nothing. para-bots
  `125087c`.)
- Add a **scheduled sweep** as the universal backstop for the residual crash
  window: a periodic launchd job (`StartInterval` + `RunAtLoad`, **not**
  `KeepAlive` per [[feedback_launchd_keepalive_crashloop]]), guarded fail-closed
  with a liveness check + activity grace. Verify it via `last exit code`, not
  `state`, per [[feedback_plist_runatload_gotcha]].
- **Symmetry check** for any "created at SessionStart" resource: ask *"what
  destroys it, and does that destroyer fire on kill/crash/timeout?"* If the
  answer is "a SessionEnd hook," it leaks.

Sibling operational-substrate-hygiene pin to [[feedback_plist_runatload_gotcha]],
[[feedback_launchd_keepalive_crashloop]], and [[feedback_hook_script_exec_bit]]
(all: a hook/launchd failure mode that is silent because the failure path is
non-blocking and invisible).

_Provenance note (2026-06-04): the first draft of this pin over-stated its
doc-cites — it invented a `/exit` reason, omitted the real `other` catch-all,
asserted "idle-timeout/terminal-close" as documented, and padded the cleanup
quote. Corrected by an adversarial docs re-fetch (freepass) the same day. The
thesis and the lazy-create+inline-destroy+sweep pattern were unaffected — only
the doc-cited specifics. A reminder that a single agent's "the docs say X" is
itself a claim to verify, per [[feedback_no_fabricated_results]]._
