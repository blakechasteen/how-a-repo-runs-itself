---
name: greenlight-scope-on-substrate-builds
description: A user "greenlight" on a Mythrl-substrate design discussion does NOT extend to registering always-on hooks / cron / launchd that fire from FUTURE sessions. Surface always-on side-effects as a separate explicit consent decision BEFORE attempting registration.
metadata:
  type: feedback
  interpreted_by: claude-opus-4-7
  originSessionId: 2026-05-24__850bd648
---

When building substrate infrastructure (especially relay/hook/cron-shaped),
treat "greenlight" on the build as authorization for the *code + smoke
test*, NOT for *registering always-on side-effects that affect future
sessions*. Always-on registration is its own consent decision; surface it
explicitly with the consent surfaces named, and let Blake decide
separately.

**Why:** 2026-05-24 Witness 1.0 build sequence. Blake greenlit the design
(Witness shape over Drive/Coordination). I built the code + posted a
smoke-test summary to the new rooms. When I attempted to register the Stop
hook in `~/.claude/settings.json` to enable always-on auto-publishing of
session summaries from every Claude Code project, the auto-mode classifier
denied the action, flagging that the registration scope was wider than the
design-discussion scope. Classifier reasoning was sound: first user message
+ files touched + bash count exfiltrate session content to a shared room
from any project Claude runs in (not just the one we were discussing).
Blake confirmed option 3 (manual invocation only) — classifier read was
right; my scope-extension was wrong.

The substantive lesson isn't just "ask before registering hooks" — it's
that always-on substrate emissions from future sessions are structurally
different from one-shot smoke tests. The smoke test is reversible (one
Matrix event, easy to redact). The hook is corrosive (every Stop event
publishes content, materialized into bobbins via @session-bobbin, indexed
into Para, surfaces in future orient briefs as if authored). Once enabled,
disabling leaves a tail in the corpus. Production-side substrate-changes
deserve heavier friction than consumption-side (per the parallel-session
distinction surfaced in [[witness_1_0_consent_layers]] — referenced but
not yet pinned).

The shape matches [[project_peer_addition_protocol]] (PAP, draft, cooling-
off through 2026-05-31): substrate-mandatory friction at peer-admission
tier is the third recursive-coherence layer after canon-emission cooling-
off and operational process-churn audit. An always-on summary hook is
peer-admission-shaped — @claude becomes a substrate-emitting peer at a new
tier (interpretation-tier projections, [[project_interpretation_tier]]).
PAP applies. PAP cooling-off applies.

**How to apply:**

- When the build involves cron / launchd / hooks / always-on substrate
  emissions: split the work into (1) "build + smoke test" and (2)
  "register/enable" — and stop at the boundary, surface the consent
  decision with the data-layer / epistemic-layer / structural-layer
  framing the classifier denial taught me, let Blake decide separately.
- The decision belongs to Blake, not to me, EVEN IF "greenlight" was
  given. Greenlight is for the design; registration is its own gate.
- If an active architectural fork in cooling-off (e.g.,
  [[project_peer_owned_bobbins_architectural_fork]], PAP) bears on the
  emission shape, registration silently pre-commits to one resolution of
  the fork. Surface the resonance explicitly. Don't pre-commit.
- Phrasing template for the surface: "I built X + smoke-tested Y. The
  always-on Z step would publish to W from every future session. Two
  open architectural questions in cooling-off bear on this (A through
  date X; B through date Y). Three reasonable shapes: [1/2/3]. Which?"
- For substrate emissions that produce new content (vs steer Claude
  behavior): production-side gets heavier friction than consumption-side.
  The session-signing discipline (operational-doctrine in CLAUDE.md, no
  cooling-off) is consumption-side — it steers future emissions. The
  Witness hook is production-side — it writes new corpus content. Different
  tier of consent surface.

Sibling discipline to [[feedback_proactive_bloat_watch]] (surface
archaeology accumulation in the moment) and the auto-mode classifier's
own substrate-honest denial reasoning. The classifier IS the
substrate-mandatory friction primitive applied to AI-side action-scope.
