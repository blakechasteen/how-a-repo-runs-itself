# Capkip Convention — the copy-pastable kickoff prompt

A **capkip** (**cap**turing **kip** — copy-pastable kickoff prompt) is the ~5-line
imperative paste that *starts* a fresh session on work that is genuinely owed to
one. It is the executable last mile of the session workflow:

```
orient → work → handoff → woosh (brief) → capkip
         └──────────── retrospective ───┘   └ prospective, imperative ┘
```

This doc formalizes a practice that **already exists** — it is documentation, not
a new ritual. Capkips have been written and delivered in real sessions for weeks;
they just had no convention, no home, and so evaporated into transcript. This is
the same move WSH made for `BRIEF_*` (`_CONVENTION.md`): name the practice, give
it a durable home, change nothing about how it works.

`_`-prefixed on purpose: like `_CONVENTION.md`, this file is **meta**, not a
workplan brief — the `handoff/brief/` parser (`brief_sweep.py`) skips `_*` files,
so a convention doc doesn't get read as a brief that forgot its `done_when`.

## What a capkip is (and is not)

It is the **fourth continuity artifact**, and it is easy to confuse with the other
three — so, disambiguated (this extends the `_CONVENTION.md` table):

| Artifact | Where | Shape | Answers |
|---|---|---|---|
| **orient brief** | `hololoom_orient` (generated) | ~3k-tok digest | "What is this whole project, right now?" |
| **session handoff** | `handoff/sessions/<ended>__<sid8>.json` | frozen per-session JSON snapshot | "What happened in *that* session?" |
| **work-brief (WSH)** | `handoff/brief/<topic>.md` | standing prose spec | "Pick up *this thread* and carry it." |
| **capkip** | the `capkip` field of a handoff (see *Where it lives*) | ~5-line imperative paste | "**Paste this to *start* the next session on the owed work.**" |

A capkip is the **imperative bridge** between a standing brief (prospective, but
prose) and a *specific fresh session actually starting*. It is a **projection of
an already-written brief into imperative form** — not new content. If there is no
brief, there is usually no capkip: write the brief first, then project it.

The load-bearing distinction from a brief: a brief carries the *why* (reasoning,
options, tensions); a capkip carries only the *how-to-start*. Keep them separate —
see the watch-out below.

## The canonical shape

~5 lines, each answering one question the fresh session would otherwise re-derive:

```
1. orient line     →  orient topic=<lens-or-topic>        (bootstraps context)
2. read pointer    →  Read handoff/brief/<brief>.md        (the standing spec)
3. first safe step →  <the one action safe to start now>   (kills cold-start hesitation)
4. order/guardrail →  <sequence + what NOT to touch>       (collision + scope safety)
5. done signal     →  done_when: <predicate>               (mirrors the brief; when to stop)
```

"~5" is a guideline, not a template. Line 3 (the first safe step) legitimately
expands into an ordered checklist when the owed work is itself a short sequence
(the ChatOps go-live below is exactly this). The invariant is not the line count —
it's that every line answers a *would-otherwise-re-derive* question, and nothing
more. A capkip that grows past a screen has started absorbing the brief.

## Worked examples (real, grounded)

Three capkips from the live corpus. Note the third: it kicked off *this very
convention* — Blake reached for the canonical shape unprompted, which is itself
evidence the shape is natural rather than invented.

**1 — LBP build plan** (`ed6113db`, 2026-07-04):
```
orient topic=lbp-primitives
Read handoff/brief/lbp_build_plan_v1.md
work S0→S3 in order; S0 (orient-card fix + pin verdict fold) is safe to start immediately
```

**2 — ChatOps go-live** (`4c8482f8`, 2026-07-03): a capkip whose first-safe-step
expanded into the exact last-leg provisioning checklist (@claudeops account+token
→ create #chatops rooms → promote friend guest→collaborator + flip `run` enabled
→ set API keys → re-prove jail → live consented run → flip both chatops briefs
`consumed`). The "order/guardrail" line mattered most here — a live-provisioning
sequence where step order is load-bearing.

**3 — this convention** (`00098682`, 2026-07-04): Blake's kickoff paste —
`formalize capkip` / `orient handoff-ritual` / `Read handoff/brief/capkip_convention.md`
/ `Start: write the CONVENTION doc…` / `Order/guards: convention first → optional
field; DEFER the generator; keep OPTIONAL…` / `Done: shipped OR declined OR
auto-declines 2026-09-01`. Canonical five lines, verbatim.

All three were written, all three were load-bearing, and two of three evaporated
into transcript. That evaporation is the gap this convention closes.

## Where a capkip lives

A capkip persists in the **optional `capkip` field of the session handoff**
(`.claude/skills/handoff/SKILL.md` schema; rides into
`handoff/sessions/<ended>__<sid8>.json` at `/handoff`, and is text-indexed in the
`sessions` corpus). An optional companion `owed_to` (`fresh` | `<topic>`) records
who the kickoff is for.

This is the "slice of A" the capkip brief recommended: the field makes an owed
kickoff a **tracked, addressable, searchable** artifact instead of ephemeral chat.
Today the next session reaches it by reading the prior handoff (which orient
surfaces as `related_sessions`) or by `search corpus=sessions`. Orient
*auto-surfacing* it ("a kickoff is owed for topic X") is a **deferred follow-on**
(server.py change — see *Deferred* below); the field is the durable home now,
auto-surfacing is polish.

A capkip is also fine to just paste in-conversation when the owed work starts
*this* session or the next one immediately — the field is for when the kickoff
would otherwise be lost to transcript. Persist when it's owed to a *later* session;
paste inline when it's owed to the *next* action. Both are valid.

## The one load-bearing property: suggestion, not directive — downstream too

A capkip is a kickoff **offer**, not an order. The receiving session stays free to
reshape or decline it — the autonomy thesis at the coordination layer, the exact
property WSH guards for briefs (`_CONVENTION.md`). The imperative *mood* ("orient…
→ Read… → start with…") is a convenience, not an obligation: the paste says
"here's the fast path," never "do exactly this." A capkip that reads as a binding
command has rebuilt the task queue one layer down — which is the failure the whole
brief/capkip surface exists to avoid. Keep the imperative mood, keep the negotiable
status.

## Guardrails

- **Optional, never a mandatory handoff step.** The handoff ritual is already
  heavy; a capkip is written *only when work is genuinely owed to a fresh session*
  — most handoffs carry none. A required capkip step would worsen ceremony-creep,
  not fix it. The field is optional precisely so it adds zero mandatory work.
- **Keep it thin — don't let it absorb the brief.** If capkips start carrying the
  *reasoning* (why, options, tensions) rather than the imperative projection of it,
  they've become briefs with worse frontmatter. The brief stays the home for the
  why; the capkip stays a ~5-line pointer.
- **No new always-on machinery** (`feedback_greenlight_scope_on_substrate_builds`).
  Ship the field + this convention; no cron, no hook, no auto-generation without an
  explicit go.
- **CLAUDE.md is not edited by this artifact.** If capkip should be named in the
  *State continuity* section of `CLAUDE.md` beside handoff/woosh, that rides as a
  separate `claudemd_capkip` structural proposal under the amendment procedure —
  this convention does **not** unilaterally edit CLAUDE.md.

## Deferred (probe-before-build)

- **A `/capkip` generator skill.** An invokable skill that emits the canonical
  shape from current session state (option B in the brief). Deferred until the
  convention proves it wants one (`feedback_probe_before_build`) — a generator
  before we know we need one is ceremony risk.
- **Orient auto-surfacing.** Having `hololoom_orient` read the `capkip` field of a
  related session and surface "a kickoff is owed for topic X." A server.py change;
  do it when the field has enough live use to justify the wiring.

## References

- `handoff/brief/capkip_convention.md` — the originating WSH brief (the SWOT that
  surfaced capkip as fault-line #3, the option analysis, the recommendation this
  doc implements). Flipped `consumed` when this shipped.
- `handoff/brief/_CONVENTION.md` — the WSH contract + the continuity-artifact table
  this one extends.
- `.claude/skills/handoff/SKILL.md` — the schema carrying the optional `capkip` /
  `owed_to` fields.
- Real instances: `handoff/sessions/2026-07-04T03-44-00Z__ed6113db.json`,
  `handoff/sessions/2026-07-03T17-29-25Z__4c8482f8.json`.
- Pins: `project_routines_and_rituals_distinction` (routine, not ritual — keep it
  flexible), `feedback_bounded_working_artifact_cadence` (smallest real slice),
  `project_cross_session_coordination` (a capkip is a coordination artifact, not
  just memory).
