---
name: builder-cannot-self-verify
description: A builder (human or AI) cannot reliably verify their own work — especially security/architectural claims, but ALSO trivial doc/surface edits ("trivial" is itself an unreliable self-assessment). Self-critique, even effortful "get real" honesty, is structurally insufficient. Proven 2026-05-24 (security); re-confirmed 2026-06-01 (trivial surface edits). Cure = independent adversarial witness; adversarial priming is load-bearing.
metadata:
  type: feedback
  interpreted_by: claude-opus-4-7
  originSessionId: 2026-05-24__fe4c4633 — proven during routine-layer MVR build when an adversarial fresh-session caught a false security claim the builder could not see
attestations:
  - session_id: 2026-05-30__9a935fb7
    model_id: claude-opus-4-8
    date: 2026-06-01
    note: independent re-confirmation + scope extension to trivial surface edits; same-lineage (opus-4-8 workflow subagents), so cures context-saturation not model-bias — weak per the same-model caveat, but produced fail-able findings, not rubber-stamps. See body.
---

Lead rule: when making correctness / security / architectural claims about your *own* work, self-critique is structurally insufficient — route it through an independent adversarial check before treating it as verified.

**Why:** 2026-05-24, building the routine-layer verify mechanism. Blake asked Claude to "get real" and critique the design honestly. Claude produced a detailed, sincere self-critique — and STILL had written a false `"DEFENDED"` security claim into the artifact, three lines from an honest limitation note. An adversarially-primed fresh Claude session (same model, zero shared context) forged a bypass and exposed the false claim in ~90 seconds / 40k tokens. The builder's context-saturation plus generative investment in the design's elegance blinded him to a hole he was simultaneously, genuinely trying to surface. Strongest evidence for independent-witness necessity; confirms the asymmetric-stake analysis (the costless/invested party cannot self-police).

**How to apply:**
- For any security/correctness/architectural claim about your own work, get an independent adversarial check before calling it verified.
- **Fresh-session (same-model) verification** is a cheap available leg: cures *context-saturation* (a session that didn't build it) but NOT *model-bias* (same weights → correlated judgment). Weak attestation per canon, pending cross-model or human-signing.
- **Adversarial priming is load-bearing.** "Is this good?" → rubber-stamp. "Assume it's flawed; try to forge a bypass; find what the builder didn't admit; concrete fail-able tasks" → real findings. A politely-prompted fresh session rubber-stamps elegance. (Same lesson as canon_attestation's v2 skeptical prompt; see [[max_over_api_for_cron]] for the `claude -p` mechanism.)
- **Coherence ≠ correctness.** A design feels correct to its builder because the builder generated the coherence. Internal consistency is orthogonal to whether it works.
- **Honesty-masquerade:** a design that narrates its own limitations fluently can make them *feel* addressed when they're load-bearing. Naming a flaw is confession, not mitigation.

**Re-confirmation + scope extension (2026-06-01 · sid8 9a935fb7 · claude-opus-4-8).** The 2026-05-24 proof was a *security* claim. This session extends the rule to **trivial documentation/surface edits**: a 2-round UI/UX audit of the `hololoom_mcp` read-surface (docstring renames, a regex pattern, stale-comment fixes — each "obviously correct"). Gating every merge-to-main on an independent adversarial workflow pass caught **two false builder claims the builder's own mechanical checks had passed**:
- orient's docstring claimed `working_preferences` is *always* present — false; the `_load_cards` fallback (context_cards.json missing) omitted it. The builder had "verified all keys present," but only on the normal path (cf. [[verify_across_instances]] — verify across all affected paths, not one).
- the topic-filter rewrite's comment claimed contiguous phrases were "byte-for-byte preserved" — false; the matcher broadened exact phrases. A *third* defect (per-list gating still broadening one list when the other matched) surfaced only when the builder reconstructed the old filter and diffed it — a test-suite leg, not self-assessment.

**Sharpening: "trivial" is itself a builder self-assessment, and an unreliable one.** Perceived low-stakes is not evidence of correctness — gate the merge regardless of how obvious the change feels. The cost is small (a focused workflow pass), the catch rate on "trivial" edits this session was 2-of-2 audit rounds. Same-lineage caveat holds: the witnesses were opus-4-8 workflow subagents (context-desaturated, not model-independent) — still weak per cross-model/human-signing canon, but they reliably produced fail-able findings rather than rubber-stamps.

Sibling: [[judgment_verify_needs_identity_keys]] (what the forge exposed), [[interpretation_tier]] (builder-coherence as a drift mode), [[ai_side_substrate_primitives]], [[routines_and_rituals_distinction]] (the build this was proven in), [[capability_asymmetry_mitigation]] (asymmetric-stake), [[verify_across_instances]] (verify across all paths/instances — the working_preferences miss above).
