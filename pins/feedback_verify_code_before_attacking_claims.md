---
name: feedback_verify_code_before_attacking_claims
description: For adversarial review of canon/claims that reference a running system, verify the code-claims FIRST — cheap, non-correlated, immune to model-bias. Same-model semantic-only attack loops; code-verification breaks the loop and often reveals the central claim is already stale.
metadata:
  type: feedback
interpreted_by: claude-opus-4-8
originSessionId: 2026-05-29__c2a9c7fa — adversarial-creative pressure-test of project_responsibility.md; reading the actual session_chain.py verify() broke the prior session's same-model fixed point and surfaced two stale flagship claims
---

When a pin (or any claim) makes a concrete assertion about a running system —
"verify() has a forgery hole", "the Merkle selective-disclosure primitive is
already built" — **read/run the code before attacking the philosophy.** Code-
verification is cheap, non-correlated (immune to model-bias / Claude-lineage
correlated-judgment), and frequently dispositive. On 2026-05-29 both of
`project_responsibility`'s flagship concrete claims turned out **stale**: the
forgery hole was closed 2026-05-28 (verify() now fails closed against an
external `allowed_signers`), and the cited "Merkle forgetting primitive already
in session_chain" never existed (grep returned zero). A subagent then *executed*
a forge that exposed a real, previously-unnamed anchor-integrity gap (the trust
root is the one un-git-tracked, owner-writable file) that no amount of semantic
argument had found.

The failure mode this fixes: `b9f03ba5` attacked the same pin purely at the
semantic layer (same-model `adversary.py`) and hit a **"detection-without-exit
fixed point"** — a witness drawn from the loop's own generative distribution
sees the problem but cannot break it. **Code-verification is the exit**: it
injects ground truth from outside the model's distribution, and CONSTRUCTION (a
build-spec derived from the verified facts) finishes the break. For whatever
stays interpretive after the facts are nailed, pair it with a genuinely
out-of-lineage witness (cross-model) — and do not let a correlated same-model
panel outvote that one independent witness (it happened here on the
bilateral-vs-consequential naming; cross-model gemma was right).

**Why:** a pin *about* provenance-integrity carried two false claims about its
own example for a full day — the exact drift it warns against. Coherence ≠
correctness ([[feedback_builder_cannot_self_verify]]); apparent/claimed state ≠
ground state ([[feedback_measure_flow_not_pose]]). The cheapest disproof of an
elegant argument is usually a checkable fact.

**How to apply:** (1) extract the claim's checkable code-assertions; (2) read
the file / run the function / grep for the cited mechanism BEFORE fanning out
opinion-agents; (3) feed the verified facts INTO any adversarial agents so they
attack reality, not the artifact's self-description; (4) reserve cross-model for
what remains interpretive, and weight it over a correlated same-model panel.
Sibling to [[feedback_probe_before_build]] (probe reality before scoping) and
[[project_routine_verify_triad]] (loud-failure gate / independent verification /
use-as-test-suite).
