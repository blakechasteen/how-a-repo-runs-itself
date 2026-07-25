# CLAUDE.md — canon-emission history & provenance

Dated narrative relocated out of `CLAUDE.md` by the `claudemd_trim` structural
proposal (ratified 2026-06-14, sid8 f9212075; brief authored 948a9a68, attested
439e4d4b + 4044a3c3). The **operative rules** stay in `CLAUDE.md`; this file
holds the *why-and-when* — the changelog a session does **not** need inline at
decision time. The operative list of *which* pins are top-of-canon lives in
`CLAUDE.md` → Architecture pointers.

---

## Operating-protocol incident log

**2026-05-27 — the concurrent-edit collision that mandated worktrees.** Two
parallel sessions' uncommitted edits mixed in the shared `main` working tree; a
commit had to be hand-extracted hunk-by-hunk from the two sessions' interleaved
`server.py`. This is the motivating incident behind the worktree-per-session
REQUIRED protocol. Same day, `SESSION.json` was gitignored (per-worktree local
scratchpad) so live state never enters a merge.

## Cooling-off efficacy note (MAST self-audit 2026-06-19)

No traced instance of cooling-off *catching* a premature promotion exists in
the corpus to date — but a deterrent leaves no trace when it works, so this is
**not** evidence it underperforms (N=7; absence ≠ failure). Retained as
precaution; revisit only if a promotion is ever actually blocked by it, or
under a cross-model audit pass.

## Top-of-canon pin discipline — rationale (2026-05-11)

The discipline exists because **2026-05-11 produced ~8 top-of-canon pins within
~10 hours, with no architectural friction applied to canon-writing rate.** The
canon itself names mandatory-friction-at-high-stakes-decisions as
substrate-mandatory (`project_architectural_safety_substrate`); canon writing at
that rate exhibited the absence of that primitive. The discipline (cooling-off,
multi-session attestation, reasoning-bobbin, tensions-with) is the recursive
coherence fix — the substrate's own production following the substrate's own
primitives.

## Grandfather cohort (cooling-off elapsed 2026-05-18)

Top-of-canon pins emitted before 2026-05-12 — **north_star, autonomy_thesis,
myth_in_mythrl, architectural_safety_substrate, capability_asymmetry_mitigation,
ai_side_substrate_primitives, packs_ecosystems_architecture,
anvil_team_coordination_layer** — cleared the 7-day cooling-off window on
2026-05-18. Multi-session attestation tuples were added to each pin's frontmatter
during cooling-off (2026-05-13 confirm passes; one amend-during-cooling-off on
`architectural_safety_substrate` 2026-05-16).

The discipline caught real issues even within same-model attestation: the
2026-05-16 hidden-alignment-engineering lens caught a D1/D2 equivocation in the
safety pin, producing `project_substrate_as_constitution` as the resolving
sibling (itself tripwire-lifted 2026-05-23 — `gates:` frontmatter encodes
condition-(iv) operational tripwire; review 2026-08-23) rather than a silent
canonization.

## Cross-model attestation chronology

All attestations through 2026-05-18 were `claude-opus-4-7` across different
sessions — multi-session satisfied formally, but correlated-judgment-failure
shape (HBP Minyan) applied honestly. The first cross-model attestation
(`mlx-community/gemma-4-26b-a4b-it-4bit`) landed 2026-05-19 with substantive
critique driving body amendment of `project_substrate_as_constitution` — the
first attestation under genuinely independent model lineage.

Pins are attestation-confirmed in the formal multi-session sense. Same-model
attestation across distinct sessionIds still counts toward the
discipline-as-written multi-session requirement, but is **weak attestation**
pending cross-model or human-signing confirmation.

**Cross-model rig run-recipe** (`~/mythrl-dev/canon_attestation/` — the directory
pointer is the operative inline copy in CLAUDE.md's amendment procedure; this is
the detailed recipe):
- `attest.py` — HTTP path against the running MLX-VLM server on `:11435`.
- `attest_mlx_lm.py` — direct-import path for any cached mlx-lm-compatible model
  from `~/mlx-bench/.venv`.
- v2 skeptical prompt that pushes past rubber-stamp shape.
- Sidecar drafts at
  `~/.claude/projects/-Users-blakechasteen-mythrl-dev/memory/.attestation_drafts/`.

## Session-signing discipline — grandfather note (2026-05-23)

Existing pins through 2026-05-23 use descriptive-only `originSessionId:` values
(e.g., "2026-05-23 — exploration after parallel-session operational substrate
work"). Retroactive sid8-augmentation is not required; new emissions follow the
discipline from 2026-05-23 forward. The 2026-05-23 attribution error in
SESSION.json on the privacy-economics ↔ peer-owned-bobbins-fork cross-reference
is the motivating instance: a `<sid8>` handle would have forced precise
attribution and prevented the AI-mediated-as-user-authored slip.

## Stack-name resolution (lifted 2026-05-29)

The "Autonomy = stack-as-noun; Mythrl = movement" lexicon distinction was in
cooling-off through 2026-05-19 and **lifted to operational 2026-05-29**
(gemma-attested, sid8 5f339d7f) — see `project_autonomy_stack_name`. CLAUDE.md
carried a stale "in cooling-off through 2026-05-19 / ripple-edits land then"
bullet until the 2026-06-14 trim; the settled one-liner now lives at
Architecture pointers.

## Canon-emission governance section gut (2026-07-13, sid8 0b6bd92d)

Blake directed a rebuild of CLAUDE.md's governance ceremony live in-session:
"keep the mechanical operating protocol, gut the canon-emission governance
section." The operative rule for each discipline stayed in CLAUDE.md,
compressed; the removed ceremony detail is preserved here rather than deleted
(`feedback_archive_not_delete`).

**Top-of-canon reasoning-bobbin (dropped from CLAUDE.md's inline discipline;
was step 3 of 4).** Before promoting a top-of-canon pin, answer three
questions: (a) why top-of-canon vs standard — what does naming it top-tier
unlock? (b) what would make it wrong — the falsifiability story; (c) what it
makes load-bearing / unblocks. The discipline was framed as self-applying:
"operational documentation here, NOT a canonized pin — it must demonstrate it
works through real friction before earning canonization. The recursive
coherence test: the substrate's own production follows the substrate's own
primitives."

**CLAUDE.md amendment — full landing steps (compressed in CLAUDE.md to:
factual-fix applies directly; structural goes through a brief + Blake
ratifies).** The full 4-step version:
1. The proposing session writes `handoff/brief/claudemd_<slug>.md` with the
   proposed diff/section, the 3-question reasoning-bobbin, and
   `tensions_with`. It does not edit CLAUDE.md directly.
2. Sessions append an attestation at `/handoff` — `{session_id, model_id,
   date, verdict: approve|reshape|decline, note}`. A witness, not a binding
   vote: same-model agreement is weak (HBP-Minyan) — prefer a cross-model
   pass or Blake's sign.
3. Once ≥1 distinct-session approve exists and cooling-off has elapsed,
   `/handoff` and the brief-sweep surface it as ready-to-ratify.
4. Blake ratifies — he (or a session he directs) merges the edit; the brief
   flips `status: consumed`.

Preferred form for step 2, as of the 2026-07 sittings: a signed tension
response (`tools/tension_attest.py attest <brief> --verdict … --note "…"`)
against a signed proposal bobbin; the frontmatter `attestations:` list is the
legacy/mirror tier. Where a signed emission exists, ready-to-ratify computes
from the signed tier, not free-text frontmatter.

**Rationale for the gut.** The accreted ceremony (formal 4-step landing
procedure, reasoning-bobbin, self-application meta-commentary) had become the
kind of bloat `project_constipated_dissipative_structure` predicts — order
bought by attention+compute, needing an attention-demotion vent. Blake
directed the cut live in conversation, which is itself the strongest form of
"Blake ratifies" the amendment procedure names — no separate brief/cooling-off
cycle was needed for a change he was actively authoring in-session.
