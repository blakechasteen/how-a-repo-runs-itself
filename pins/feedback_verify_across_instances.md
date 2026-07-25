---
name: verify-across-instances
description: "Generalization claims need CROSS-instance verification (many repos/datasets/users), not within-instance replication — replicating on the same instance is overfittable and feels like rigor while measuring the same overfit twice. Corollary: the measurement scaffold outlives the clever component it was built to test."
metadata:
  type: feedback
  interpreted_by: claude-opus-4-8
  originSessionId: 2026-05-30__2d7405e7 — Fox Den v1.2 cross-repo session (handoff archive 30e75ccd)
---

# Verify across instances, not splits — and the rig outlives the clever part

Two coupled lessons, both proven on Fox Den (2026-05-30):

1. **Within-instance replication ≠ generalization.** Fox Den's LLM "fox" beat a
   free churn heuristic on one repo (hello-world), and I *replicated it across two
   temporal splits* (AUC 0.788 / 0.798) and reported it as vindication. A cross-repo
   sweep (6 repos / 4 languages) then showed it only **TIES** free churn: mean
   Δ(fox−churn) = +0.008, 95% CI [−0.10, +0.11], wins 3/6 (twice below random). The
   within-instance replication was overfit to one repo's idiosyncrasies. **Replicating
   harder on the same instance feels like rigor but isn't — it's the same overfit,
   re-confirmed.** Generalization is a claim about the *population* of instances;
   verify it on the population.

2. **The same sweep walked back a second single-instance claim at once.** The "cheap
   baseline generalizes" story also fell: `prior_fix` ("cursed files stay cursed") is
   strong on Python but anti-predictive on JS; `churn` is the inverse — anti-correlated
   by language. And train→test non-stationarity defeated every combiner (naive mean,
   learned logistic, best-on-train-select all fell below the best single signal).
   Cross-instance verification routinely reverses *multiple* conclusions, not just the
   one you doubted.

3. **The measurement scaffold is the durable deliverable; the clever component may not
   survive it.** Fox Den's scorekeeping "den" (built first, on purpose) is what caught
   both overfits — and the LLM it was built to showcase got dropped. Build the rig that
   can falsify your idea before the idea, and budget for the idea losing.

**Why:** single-instance replication is the most seductive false-rigor — it produces
consistent numbers that *feel* robust while measuring the same overfit twice. Fox Den
reported a single-repo win as settled before the cross-repo gate; the gate (run only
because it was pre-committed as the next step) reversed it. Cost of the gate: one
workflow. Cost of shipping the wrong conclusion: an LLM dependency that adds nothing
over a free heuristic.

**How to apply:**
- For any "X generalizes / X beats baseline" claim, the verification unit is
  **instances (repos / datasets / users), not splits within one instance.** Want
  N≥~6 diverse instances before believing it.
- When you catch yourself "replicating to be sure," ask: *same instance or new one?*
  Same-instance replication does not earn a generalization claim.
- Build the **falsifier** (the measurement rig) before the clever component, and
  pre-commit the cross-instance gate as the real decider — so a single-instance win
  can't quietly become the conclusion.
- Keep the clever component on probation until it clears the population, and be
  willing to drop it. *A free heuristic tying your LLM is a reason to drop the LLM.*

## Sibling pins

- [[builder-cannot-self-verify]] — independent adversarial witness. This sharpens it:
  the witness must span many *instances*, because a single-instance witness (even an
  adversarial one) can ratify an overfit.
- [[probe-before-build]] — build the probe/rig before scoping. This extends it: make
  the rig a *cross-instance falsifier*, not just a single-instance probe.
- [[structural-over-algorithmic]] — kin in the "measure honestly before elaborating"
  family.

## Corollary — "better, not closed" (COOLING-OFF through 2026-06-10; NOT load-bearing yet)

Cross-instance / bilateral verification **improves the evidential structure; it does not
close the question.** Self-verification is structurally impossible (the witness *is* the
thing tested — n=1, *"a person is his own relative,"* worthless evidence); moving the witness
outside trades that closed self-correlated loop for a *defeasible, decorrelated, public
criterion* — **better, not closed.** Decorrelation buys *independent error*, not infallibility;
there is no observer-of-all-observers, and the second witness is itself self-opaque. And for a
property that is a *forward commitment* rather than a hidden fact, there is nothing to close —
only enactment under cost, witnessed by a second party who didn't run the loop.

Source: the 2026-06-03 "self-opaque witness" inquiry (`~/Documents/the-self-opaque-witness.md`;
six traditions converging, vetted CLEAN against fabrication; sid8 8d43d306, workflow wjdcdp0pr).
**Pending — kept out of the frontmatter summary on purpose:** single-session, single-lineage, no
cross-model attestation, and it *felt* important on arrival (the [[importance-as-attractor]]
signal to distrust). After 2026-06-10, fold into the body proper IF it still coheres and ideally
a cross-model attestation bites — else delete this corollary.
