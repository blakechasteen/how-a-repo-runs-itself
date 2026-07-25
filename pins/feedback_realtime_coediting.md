---
name: real-time co-editing during sessions
description: User edits source files in parallel with Claude during a session; treat their edits as authoritative and re-read before editing
type: feedback
originSessionId: 74d158a1-bc6e-4091-9669-6685953da7bb
interpreted_by: claude-opus-4-7
---
The user actively edits files alongside Claude during long sessions — sometimes anticipating the next step, sometimes correcting framing, sometimes refining vocabulary. Their edits arrive as `<system-reminder>` notes saying "the file was modified, don't revert."

**Why:** validated 2026-05-09 across multiple files in one day — user edited `context_cards.json` (twice), `CLAUDE.md` (multiple times), `README.md`, `server.py` (added the two-tier docstring, `_SESSIONS_UUID_NS`, the `_graph_for_bobbin` / `_graph_for_session` dispatch *before* I got to it), `yarn_writer.py` (narrowed scope to artifact-only). Their edits were almost always either (a) better than what I had planned, or (b) anticipating my next planned step. Trying to revert them or paving over them was always wrong.

**How to apply:**
- Treat the `<system-reminder>` "file was modified" notes as authoritative; do not revert.
- After such a reminder, re-read the file before the next edit (avoid the "string not found" error from stale assumptions).
- If the user's edit conflicts with my next planned step, their version wins. Adjust my plan, don't argue.
- Their edits sometimes anticipate me — e.g., adding a constant or import I was about to need. Recognize this as cooperation, not duplication.
- Keep edits surgical, especially in shared files; smaller edit blocks reduce conflict probability when working in parallel.
- The pace difference is the value: I run fast on mechanical work, they run thoughtfully on framing. The session output is better than either of us alone would produce.
