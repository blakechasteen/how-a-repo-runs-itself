---
name: feedback-sid8-from-sessionid-field
description: own sid8 = $CLAUDE_CODE_SESSION_ID env var FIRST (collision-proof); else the sessionId FIELD inside ~/.claude/sessions/<pid>.json, never the filename — both heuristic paths have written wrong sid8s into canon (2026-06-07 PID fragment, 2026-06-11 idle-peer pick)
metadata:
  type: feedback
interpreted_by: claude-opus-4-8
originSessionId: 2026-06-07__222013c5 — free-pass review caught a fabricated sid8 (4005) already committed to context_cards.json
amended: 2026-06-11__d3acf969 — second recurrence (presence-heuristic picked idle peer 895b2a68); env-var-first rule added
---

**Your own sid8: `echo $CLAUDE_CODE_SESSION_ID | cut -c1-8` — the env var the
harness exports into every Bash call. Collision-proof self-identification; no
file matching, no heuristics.** (`handoff/archive.py` checks it first for the
same reason.) Everything below is the fallback path for when the env var is
absent, or when you need *another* session's sid8.

The session UUID is the **`sessionId` field inside**
`~/.claude/sessions/<file>.json` — **not the filename.** Those files are named
by **PID** (e.g. `4005.json`), so `basename | cut -c1-8` yields a PID fragment,
not a sid8. Read the field instead:

```sh
python3 -c "import json;print(json.load(open(F))['sessionId'][:8])"   # -> 222013c5
```

Match the right file by its `cwd` field; multiple live sessions share a cwd, so
also disambiguate by `updatedAt`/`status`, or cross-ref the known-OTHER sid8s
the SessionStart presence hook prints (yours is the one NOT in that list).
**Every disambiguation heuristic here has misfired in practice:** on 2026-06-11
(d3acf969) the newest-presence-heartbeat pick selected an idle peer
(895b2a68) and the wrong sid8 was committed into salvage provenance — caught
only because a later archiver run printed the env-var sid8. Heuristics guess;
the env var knows.

**Why:** On 2026-06-07 (sid8 222013c5) I committed `sid8 4005` into
`context_cards.json` canon — `4005` was the session file's PID name, not my
session UUID (`222013c5-4db1-…`). A *wrong* sid8 is worse than none: it's false
mechanical attribution — exactly the failure the session-signing discipline
exists to prevent. CLAUDE.md's "Discovering <sid8>" note says the UUID "lives in
~/.claude/sessions/*.json matched by cwd" but does **not** warn that the
filename ≠ the UUID, so the naive derivation looks reasonable and silently lies.

**How to apply:** Before signing any canon / commit / lock with a sid8, derive
it from the `sessionId` field, and sanity-check the result is an 8-hex-char
UUID prefix (`[0-9a-f]{8}`). If what you got is short or all-digits, you grabbed
the PID — stop and re-derive. Caught this on a free-pass adversarial review;
links: [[feedback_no_fabricated_results]], [[project_handoff_archive_discriminator_collision]].
