---
name: Structural fix beats algorithmic fix for noise problems
description: "When facing notification/output noise, prefer narrowing the channel's contract over adding scoring/severity rules. Confirmed in watcher v1.1 where Blake chose delta-only Matrix posts over my proposed smarter-escalation rule. Refined 2026-05-27 — delta-only has a DUAL blind spot: narrowing to transitions also makes persistent *signal* (a stuck ESCALATE) unrepresentable; cure is a narrow staleness re-nag, still structural not algorithmic."
type: feedback
originSessionId: 26e93331-87cd-4476-a376-8d8176a36606
interpreted_by: claude-opus-4-7
---
When facing a noise/alarm-fatigue class of problem, prefer a structural posture that makes the noise *unrepresentable* over an algorithmic rule that *filters* it.

**Why:** Confirmed 2026-05-09 during watcher v1.1 design. Watcher had alarm-fatigue risk: stable WARN findings would auto-escalate to ESCALATE after 3 raise cycles regardless of whether anything was actually deteriorating. I proposed making the escalation rule smarter ("require value moving wrong direction OR raise_count >= 3 with no deferral ever registered"). Blake instead implemented "Matrix only sees NEW/ESCALATED/CLEARED transitions, never stable findings" — delta-only posting. Structurally: the room *can't* display stable noise no matter how the escalation logic evolves. The rule-based filter would have dragged correctness debt forward (more conditions to maintain, more edge cases); the structural fix retired the problem class.

**How to apply:** When facing a finding/output/notification noise problem, ask FIRST whether the channel's contract can be narrowed (only show transitions, only show first occurrence, only show when value crosses a band) before reaching for a "smarter scoring/severity/escalation rule." Two heuristic signals you're about to over-rule:
1. You're adding `if X AND (Y OR Z)` to a rule that already has compound logic.
2. You're naming the rule with words like "smarter," "adaptive," or "context-aware."
Both usually mean the channel's contract is too permissive and the rule is compensating. Constrain the channel; the rule simplifies or disappears.

---

**Refinement — the dual blind spot (2026-05-27 · sid8 3336ef3b · claude-opus-4-7).** The delta-only fix above is correct, and it carries a *symmetric* cost worth naming: narrowing the channel to transitions makes stable **noise** unrepresentable — but it equally makes stable **signal** unrepresentable. A finding stuck at ESCALATE is not a transition, so a real unfixed outage pings once (as NEW) and then goes permanently silent — the longer it stays broken, the quieter it gets. Proven 2026-05-27: the watcher's voice/materializer ESCALATEs had raised 196× since 2026-05-10 yet produced a single Matrix post, and `negative_space.py` (a *semantic* tool reading session prose) was what resurfaced the outage. The operational tool had landed in the exact failure mode — "silent slippage, corrosive by accumulation" — that a different tool exists to catch.

The cure stayed structural, not algorithmic: a `STALE` re-nag (watcher.py `apply_state`, merged 8383e4a) *manufactures* a transition at a fixed interval (`WATCHER_STALE_RENAG_EVERY_H`, default 72h) for any finding still at ESCALATE — so persistence becomes representable again, with no scoring rule. **Generalized: when you narrow a channel's contract to kill noise, check the dual — does the same narrowing also suppress a class of *important persistent* state? If so the contract needs a second, equally-narrow channel for persistence (a periodic re-assert), not a relapse to permissive scoring.** Coheres with [[feedback_max_over_api_for_cron]] (watcher's `translate_rollup` reference) and the negative-space thesis that absence is invisible by default.
