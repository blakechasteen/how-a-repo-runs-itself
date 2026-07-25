# Workplan Suggestion Handlers (WSH — "Woosh")

`handoff/brief/*.md` is the home for **workplan suggestions**: standalone,
human-renderable documents that *propose* a unit of work to a future session.

This is the missing surface between the two we already had:

- `handoff/sessions/*.json` carries forward-intent as terse `open_threads`
  pointers, buried in one session's retrospective JSON.
- memory pins carry durable canon.

Neither is a *prospective, standalone, readable workplan*. A WSH is. The
motivating instance: the project-C opener from session `2d7405e7`
(2026-05-30) wanted a durable home and had only two bad options — bloat the
JSON archive, or stay paste-only in-transcript (ephemeral). It chose
ephemeral. This directory is the third option. (Organic precursors already
existed under `handoff/` root: `BRIEF_*.md`, `RESUME_*.md`. WSH formalizes
that practice rather than inventing it.)

A brief is the **third continuity artifact** in this repo, and it's easy to
confuse with the other two — so, disambiguated:

| Artifact | Where | Shape | Answers |
|---|---|---|---|
| **orient brief** | `hololoom_orient` (generated) | ~3k-tok digest | "What is this whole project, right now?" |
| **session handoff** | `handoff/sessions/<ended>__<sid8>.json` | frozen per-session JSON snapshot | "What happened in *that* session; what are its open threads?" |
| **work-brief** | `handoff/brief/<topic>.md` (this folder) | standing prose spec, lives until done / declined | "Pick up *this one thread* and carry it forward." |

A session handoff is a **snapshot of a session**; a brief is a **standing
work-item** that outlives any single session (a handoff's
`open_threads[].next_step` often *points at* a brief). Getting this distinction
wrong is how a brief lands in the wrong place — the table is the guardrail.

> Provenance: this table is folded in from a parallel session's transient
> `README.md` for this directory (untracked, since removed), consolidated here
> so `_CONVENTION.md` stays the single canonical doc.

## The one load-bearing property: suggestion, not directive

In LBP terms a WSH is a **Tension-opener**, not a command. It proposes; the
receiving session negotiates — accepts, modifies, declines. That preserves the
receiving session's agency (the autonomy thesis at the coordination layer). If
briefs ever become work a session feels *obligated* to execute, we've rebuilt
a task queue and lost the property that makes this substrate-native. Keep the
word **suggestion**.

## Frontmatter contract (YAML between `---` fences)

Required:

| field | meaning |
|---|---|
| `title` | human-readable one-liner |
| `status` | `open` \| `consumed` \| `superseded` \| `declined` |
| `created` | `YYYY-MM-DD` |
| `done_when` | the **explicit retirement condition** — the anti-bloat discipline. **Enforced:** a brief missing `done_when` is skipped by orient (logged), not surfaced. No open-ended briefs. |

`done_when` is the **only** field the orient parser hard-enforces (skip-on-missing); the rest are conventions the parser reads softly (`fm.get(..., "")`) and will not reject a brief over.

### done_when shape — prefer mechanical (pinned 2026-07-02)

Write the most mechanical shape the retirement condition honestly admits
(pin: `feedback_done_when_mechanical_shape`; evidence at pinning: 19/19
sweep-surfaced retirables routed `needs_attestation`, zero mechanical closures
in the corpus's history):

1. **Dated backstop** — "…OR untouched by YYYY-MM-DD → auto-declines." The only
   shape `done_when_eval` may close unattended (the author set the deadline;
   the machine just reads it back).
2. **Evidence predicate + exact command** — "X merged / test green — check:
   `<cmd>`." Never auto-flips (fail-closed by design), but turns the human flip
   from a judgment into a one-command confirm.
3. **Numeric threshold + named queryable source** — a bare number routes to
   `needs_attestation` ("no DB query"); say where the number is read from.
4. **Manual/judgment** — legitimate only when retirement genuinely IS a
   decision; name the decider and the options ("Blake picks A/B/C"). Never
   Goodhart a real judgment into a proxy metric.

Default composition: **mechanical primary + dated fallback**, so no brief can
rust open.

Provenance (per the memory-provenance discipline):

| field | meaning |
|---|---|
| `sid8` | session that authored the **workplan content** (first 8 of the session UUID). Strongly recommended — provenance, and the handle a future session cites. Soft (not parser-enforced); a relocated brief may carry `rescued_by` instead/as well. |
| `rescued_by` | `sid8` of a session that *moved/repaired* a brief it did not author (e.g. the R2-3 relocation). Distinct from `sid8` (authorship) — use when the two differ. |
| `interpreted_by` | model id if AI-synthesized (e.g. `claude-opus-4-8`); **omit** if Blake hand-authored. Absence = user-authored. |

Optional:

| field | meaning |
|---|---|
| `topic` | slug used for pull-routing; match an `active_threads` topic when one exists (e.g. `autonomy-measurement`). **Match is case-insensitive *substring* against `topic` + `title`, not exact-slug** — so a hint matches any brief whose topic or title contains it. Keep slugs distinct enough that substrings don't cross-match. |
| `global` | `true` if this brief should reach **every** fresh session, not just topic-hinted ones. Use sparingly — only for load-bearing next-work that genuinely warrants shouting at everyone. Default (absent) = topic-gated. |
| `reads_with` | list of pin slugs / brief filenames for context |

The body below the frontmatter is freeform markdown — use whatever structure
the work wants (the organic `BRIEF_*` shape: why / question / steps /
guardrails / references is a good default).

## Lifecycle

- **open** → surfaced by orient (see pull semantics). The live state.
- **consumed** → the `done_when` condition was met. Set `status: consumed`;
  leave the file in place (archive-don't-delete). Orient stops surfacing it.
- **superseded** → a newer brief replaces it. Set `status: superseded` and
  reference the successor in the body.
- **declined** → the proposed work was considered and rejected (won't-fix).
  Set `status: declined`; record why in the body. Distinct from `consumed`
  (the work was done) — a `done_when` that ends "…OR the finding is explicitly
  declined" retires here, not at `consumed`.

`done_when` is mandatory precisely so this directory cannot become archaeology
sprawl — every brief declares the condition under which it stops being live.

**The collector** (`tools/brief_sweep.py`, run as `/handoff` step 5) is what
keeps this lifecycle from rusting open. It is a *candidate surfacer*, not an
auto-popper: `done_when` is almost always a prose judgment predicate, so it
cannot be machine-evaluated, and auto-flipping would break the one load-bearing
property above. The sweep flags briefs that *look* retirable (a passed
`done_when` time-expiry; a `claudemd_` proposal past `cooling_off_until`; topic
match to files touched this session; long-open + git-untouched), and the
session/human confirms each flip via `brief_sweep.py flip <brief> --to <status>`
(a safe one-shot frontmatter edit, so provenance isn't stubbed). Surfacing, not
deciding.

## Disposition records (opt-in engagement events)

The 4-state lifecycle records terminal *status*, but the convention's one
load-bearing property is **engagement** — accept / **reshape** / decline. Two of
those are invisible to status: **reshape** has no state (accept-with-modification
just flips to `consumed`), and a decline's **why** is per-file free text that
doesn't aggregate. The disposition-census (`tools/brief_disposition_census.py`)
measures what it can from status + git; this surface captures the rest.

`tools/brief_disposition.py record <brief> --kind reshaped|declined|deferred|accepted
--why "…" --sid8 <you> [--into <successor>]` appends a small append-only event
record to `handoff/brief_dispositions/<ts>__<slug>__<sid8>.json` (mirrors the
`handoff/reattestations/` shape). The census reads them back — reshape becomes a
real (opt-in *floor*) count, the whys aggregate — and `hololoom_fleet`'s
`open_briefs.disposition` headline surfaces `reshape_recorded`.

**Guardrails (non-negotiable — they keep the fix from becoming the disease):**

- **Opt-in / never blocking.** Recording is NEVER a mandatory handoff step. If
  *not doing* a suggestion became expensive to record, sessions would drift back
  toward just executing briefs — the task queue this whole convention forbids.
  The writer fail-soft-returns on any error; it never aborts a caller.
- **WITNESS, never a KPI.** No decline/reshape-rate target. The count is a floor
  (only volunteered records) reported as a mix, never optimized.
- **Structural, not algorithmic.** A narrowed channel, not an engagement score —
  no per-brief scoring, ranking, or nudges. It records what you volunteer and
  reads it back; it never prompts.

Sibling to the `fifth_discipline` `suspended:` idea — record what a pass *gave
up* and why, so team-learning doesn't evaporate. (Option B of
`brief_decline_visibility.md`, greenlit 2026-07-05.)

## CLAUDE.md amendment proposals (`claudemd_` briefs)

A `claudemd_<slug>.md` brief is a **structural-edit proposal for CLAUDE.md**,
routed here because CLAUDE.md is top-of-canon-tier and its structural edits go
through the top-of-canon discipline rather than landing unilaterally (see the
"CLAUDE.md amendment procedure" section in `CLAUDE.md`). It is a
standard WSH brief plus these fields:

| field | meaning |
|---|---|
| `proposal_target` | the file being amended — `CLAUDE.md` (room to generalize later) |
| `change_class` | `structural` (gets the full cycle) \| `factual-fix` (applied directly, no proposal needed — this brief shape is only for `structural`) |
| `cooling_off_until` | `created` + 7 days; ready-to-ratify only after this date |
| `attestations` | inline list of `{session_id, model_id, date, verdict, note}` tuples appended at `/handoff` — a witness, not a binding vote (same-model agreement is weak attestation) |

The body carries the **reasoning-bobbin** (the 3 top-of-canon questions: why
top-tier / what would make it wrong / what it unblocks) and a **tensions-with**
section. Lifecycle is the standard one below: `open → consumed` (Blake ratified
+ merged) / `declined` / `superseded`. The suggestion-not-directive property
still holds — the gate is on *unilateral structural editing of CLAUDE.md*, not
on accepting any given proposal. Precedent: `claudemd_governance.md` (the
bootstrap that established this).

## Pull semantics (how a brief reaches a session — "Woosh")

**Pull, not trigger.** `hololoom_orient` scans this directory and surfaces
`open` briefs as a `workplan_briefs` field. Surfacing is **topic-gated by
default** — a brief shows only if it either:

- opts into global advertisement (`global: true`), or
- matches a `topic` hint the session passed to orient.

So a **no-hint** orient surfaces only `global` briefs — it does *not* dump
every open brief. That's deliberate: an advertise-everything-to-everyone
default is the alarm-fatigue trap (`feedback_structural_over_algorithmic` —
narrow the channel's contract, don't add scoring). `global` is the explicit,
sparing opt-in to shout.

Orient returns only the pointer (title / topic / sid8 / path) — progressive
disclosure; the session `Read`s the full brief (done_when, reasoning, steps)
on demand. No event-handler registration, no cron, no always-on machinery —
that "handler" reading is deferred until a real triggering need appears
(greenlight-scope: no always-on triggers without explicit opt-in).

## Deferred (probe-before-build)

- **Corpus indexing.** Briefs are orient-surfaced only; not in
  `hololoom_search`. Add an artifact-tier indexer only if briefs accumulate
  durable reference value.
- **HTML rendering.** Markdown now. HTML (rendered workplan board / publishable
  surface) when a human-facing-render need is real.
- **Genuine handler/trigger semantics.** Pull is v1.

## Parser notes

- Files beginning with `_` (like this one) are meta, not briefs — skipped.
- Frontmatter is parsed dependency-free (no PyYAML); keep values to simple
  `key: value` scalars and `[a, b]` inline lists.
