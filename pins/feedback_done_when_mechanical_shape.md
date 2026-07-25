---
name: Steer done_whens toward mechanical shape
description: When authoring a brief's done_when, prefer machine-checkable shapes — dated backstop (the only clause allowed to auto-close), evidence predicate with the exact check command, numeric threshold naming its queryable source. Honest manual/judgment ONLY for irreducible decisions, naming the decider + options. Evidence 2026-07-02 — 19/19 sweep retirables routed needs_attestation; zero mechanical closures ever.
type: feedback
originSessionId: 2026-07-02__5de56efa — Pinsmith disposal assessment; Blake asked to pin done_when steering
interpreted_by: claude-fable-5
---
**Rule.** When writing a brief's `done_when`, pick the most mechanical shape the
condition honestly admits, in this order:

1. **Dated backstop** — "…OR untouched by YYYY-MM-DD → auto-declines." The ONLY
   shape `done_when_eval` may close on its own (the author opted into the
   deadline; the machine just reads it back).
2. **Evidence predicate + exact command** — "X merged / test green / exit 0 —
   check: `<cmd>`." Never auto-flips (by design), but turns the human flip from
   a judgment into a one-command confirm.
3. **Numeric threshold + named queryable source** — a bare number routes to
   `needs_attestation` ("no DB query"); say where the number is read from.
4. **Manual/judgment** — legitimate ONLY when retirement genuinely IS a
   decision. Name the decider and the options ("Blake picks A/B/C"). Never
   Goodhart a real judgment into a proxy metric.

Compose them: mechanical primary + dated fallback is the strong default shape.

**Why.** `done_when_eval` (Pinsmith slice 1) is fail-closed by construction —
auto-evaluating prose/numeric predicates would let a session retire its own
proposals and convert the suggestion-queue into a task queue. So mechanical
closure can only come from AUTHORSHIP, and the corpus starves it: 2026-07-02
sweep, 19/19 retirable candidates routed `needs_attestation`; zero mechanical
closures in the corpus's history. Every judgment-shaped done_when spends the
pile's binding constraint — Blake's decision-time
([[project_mast_self_audit_verdict]]). Same mechanical-vs-judgment split as the
Proof Block discipline, applied prospectively; judgment-class verification
stays human until identity-keys ([[project_judgment_verify_needs_identity_keys]]).

**How to apply.** At brief-authoring time, ask "what command would a stranger
run to confirm this is done?" and write that into the predicate; add the dated
fallback so the brief can never rust open. Keep `manual` honest rather than
dressing it mechanical. Retirement is the brief-pile's entropy vent
([[project_constipated_dissipative_structure]]).
