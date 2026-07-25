# MAST Self-Audit of the Mythrl Coordination Substrate

*2026-06-19. Read-only findings doc — companion to [`agent_harnesses_sota_2026-06.md`](./agent_harnesses_sota_2026-06.md).*
*Commissioned by `handoff/brief/anvil_mast_self_audit_probe.md` (arc sid8 `66c4ce1d`).*

**What this is.** The agent-harness SOTA's load-bearing reliability result is **MAST/MASFT** —
the Multi-Agent System *Failure* Taxonomy (Cemri, Pan et al., UC Berkeley, NeurIPS 2025;
arXiv 2503.13657): 14 fine-grained failure modes in 3 categories across 1,600+ annotated
traces, with the headline that **failure is organizational, not model-weakness** (a
well-designed MAS beats a poorly-designed one on the same base model, +15.6%). We *claim*
our coordination substrate — worktree isolation, the handoff archive, multi-session +
cross-model attestation, cooling-off, `coord.py` locks — reduces exactly these modes. **We
had never checked.** This is the check: the MAST taxonomy run over our own trace corpus.

**Who ran it.** A fresh, non-builder Claude instance (Opus 4.8), dispatched read-only by
session `f547e5fe` (the builder-cannot-self-verify discipline applied to the coordination
layer itself). The hard-artifact spine was then independently re-verified by a *second*
distinct instance (session `f547e5fe`) — see §1.

> **Correlation caveat (load-bearing).** Labeler and verifier are the *same model family*
> (Opus 4.8) as the substrate's builders. Per `project_capability_flooring_correlation` /
> HBP-Minyan, same-model agreement is **weak** on interpretive judgments. Hard-artifact
> labels (a commit SHA, a file rename, a frontmatter count) are model-independent and
> high-confidence; **interpretive** labels are flagged for cross-model recheck in §8.

---

## 0. Bottom line

**The substrate PARTLY reduces the failure modes its builders claim.**

- **Proven control.** The **attestation / distinct-instance** primitive demonstrably catches
  verification failures (MAST 3.2/3.3) — `builder_cannot_self_verify` working in the field.
  The **handoff archive** mediates multi-session work and catches redundant builds at merge
  without clobber. *This audit itself is an instance of the control working* — it caught a
  factual error in the commissioning brief (§6, foxden).
- **Overclaimed.** **Worktree isolation does NOT zero-out write-collision** — it moved the
  collision *edit-time → merge-time* and *content → namespace*, and the collision **recurs
  after adoption**. **`coord.py` locks** show near-zero demonstrated effect and are
  **sandbox-blocked** (the SessionStart hook tells every session to run a command that
  fails). **Cooling-off** is a practiced ritual with no traced instance of it *catching* a
  premature promotion.
- **Deepest finding (§7).** The fleet does not exhibit peer-only failure-to-converge **only
  because Blake is the de-facto force-convergence gate.** Absence of stall is *not* evidence
  the constitutional gate can stay unbuilt — it is evidence the gate already exists as a
  human in the loop.

**Single strongest disconfirming evidence:** commit **`dc90a13`** (2026-06-19) — two parallel
sessions independently shipped `tools/closing_gate.py` for two *different* tools, both
"slice-2"-labeled, **with worktree isolation fully in force** (22 days post-adoption), caught
only reactively at merge (resolved by rename → `ritual_gate.py`).

---

## 1. Verification addendum (second-instance cross-check)

A second distinct instance (`f547e5fe`) independently re-ran the three load-bearing
*hard-artifact* claims against git/disk. **All three hold exactly:**

| Claim | Check | Verdict |
|---|---|---|
| `dc90a13` = parallel-session `closing_gate.py` collision under worktrees | two distinct sessions each added `tools/closing_gate.py` for different tools — `a5d1dec` (sid `c44c76c8`) vs this session's `d544860`→`dc90a13` (sid `4a52d4ab`), ~4 min apart, both "slice-2" | ✅ verbatim (re-derived by the 2026-06-20 distinct-session attestation) |
| foxden v1.2 was a *convergent rediscovery* (success), not "supersession of an independent v-branch" (the brief's framing) | `git show a7ef90a` ("Branch … fully superseded → abandoned, NOT merged … corroborates the drop-the-fox verdict from an independent lineage"); foxden lineage is linear | ✅ brief is wrong; corrected in §6 |
| 64% of briefs sit open (underpins §7) | `grep status:` over `handoff/brief/*.md` → 107 total: **68 open**, 33 consumed, 2 superseded, 4 declined | ✅ exact |

`coord.py`'s first slice landed 2026-06-05 (Redis presence; `a422773`), lock leg later — both
well after the E1/E3 collisions, as claimed. The **interpretive** findings (§7's
"Blake-is-the-gate", the E4 self-convergence read, cooling-off-as-unproven) were *not*
independently confirmed — they are where a cross-model pass adds value (§8).

---

## 2. The taxonomy (verified from primary source)

Verified against the ar5iv render of arXiv 2503.13657 (the GitHub `taxonomy_definitions`
file 404'd). The scaffold's 14 modes, numbers, and names were **all correct**; only
nomenclature was sharpened — the taxonomy's own acronym is **MASFT**, modes are **FM-x.y**
within categories **FC1–FC3**:

- **FC1 — Specification & System Design** (~44%): 1.1 Disobey task spec · 1.2 Disobey role
  spec · 1.3 Step repetition · 1.4 Loss of conversation history · 1.5 Unaware of termination
  conditions.
- **FC2 — Inter-Agent Misalignment** (~32%): 2.1 Conversation reset · 2.2 Fail to ask for
  clarification · 2.3 Task derailment · 2.4 Information withholding · 2.5 Ignored other
  agent's input · 2.6 Reasoning-action mismatch.
- **FC3 — Task Verification & Termination** (~24%): 3.1 Premature termination · 3.2 No/
  incomplete verification · 3.3 Incorrect verification.

---

## 3. Detectability map (honest coverage)

Our corpus keeps **handoff summaries + git history + reattestation records**, NOT raw
inter-agent message logs or live turn-by-turn transcripts. **"Undetectable" ≠ "did not
happen."**

| Mode | Detectable in our traces? | Why |
|---|---|---|
| 1.1 Disobey task spec | Partial | only if a handoff/commit self-reports deviation |
| 1.2 Disobey role spec | **Yes** | "roles" = brief scope + greenlight gates; scope-violations show in commit bodies |
| 1.3 Step repetition | Partial | cross-session redundant rebuilds visible in git; intra-session loops not |
| 1.4 Loss of conversation history | Partial/structural | can see SESSION.json clobber between sessions; not mid-reasoning truncation |
| 1.5 Unaware of termination | **Yes** | `done_when` + un-retired briefs + recurring open_threads are the signal |
| 2.1 Conversation reset | **UNDETECTABLE** | needs live dialogue logs we don't keep |
| 2.2 Fail to ask for clarification | Mostly undetectable | session→Blake event; only if a handoff notes it |
| 2.3 Task derailment | Partial | cross-arc topic-drift visible; within-session not |
| 2.4 Information withholding | Partial | the substrate's anti-withholding design = handoff; failures = collisions proving info wasn't shared in time |
| 2.5 Ignored other agent's input | Partial | visible when a session documents reconciling/retracting; silent ignoring not |
| 2.6 Reasoning-action mismatch | **UNDETECTABLE** | needs the reasoning trace vs the action |
| 3.1 Premature termination | **Yes** | `done_when` unmet + thread carried |
| 3.2 No/incomplete verification | **Yes** | the richest axis — self-cert residue, vacuous-pass bugs all logged |
| 3.3 Incorrect verification | **Yes** | logged when a later instance overturns an earlier "verified" claim |

**Undetectable: 2.1, 2.6** (and 2.2 nearly). No rate is claimed for these.

---

## 4. Sample (N = 7 episodes — a probe, not a census)

227 handoffs total; **7** multi-session episodes labeled. **Sampling rule:** from the four
declared multi-lineage arcs, select episodes that (a) involve ≥2 distinct sid8/lineages on
one topic and (b) **span outcomes** — deliberately including the two known-rocky collisions
to avoid a confirmation-biased "only smooth" sample.

| # | Episode | sid8s / lineages | Dates |
|---|---|---|---|
| E1 | `server.py` mixed-commit (pre-worktree) | 2 sessions → resolved by Blake | 2026-05-27 |
| E2 | pinsmith gate-naming collision | `4a52d4ab` vs `c44c76c8` | 2026-06-18 |
| E3 | foxden ranker + convergent rediscovery | `2d7405e7`, `7843b781` | 2026-05-29→06-14 |
| E4 | accept-gate prod-cutover reconciliation | `2093ac25` ↔ `b01e5e36` | 2026-06-16→17 |
| E5 | accept-gate S2 distinct-instance audit | `b01e5e36` → `f0a36c40`, `810160fe` | 2026-06-18→19 |
| E6 | canon-viewer divergent-viewer merge | `ec63b05c` (+`36bf930b`) | 2026-06-19 |
| E7 | reattestation DETECT+ASK drift | author `b9f03ba5`; drifters ×3 | 2026-06-03→13 |

**Sample limits:** 6 of 7 episodes are 2026-06 (recency-skewed); the four arcs are not
independent (pinsmith pivoted out of accept-gate); handoff summaries are authored by the same
agents whose coordination is being audited (self-report bias, unremovable without raw
transcripts).

---

## 5. Failure-mode profile (over the N=7 sample — NOT a fleet rate)

| Mode | Fired in | Rate | Note |
|---|---|---|---|
| 2.4 Information withholding (write/merge collision) | E1, E2, E6 | **3/7** | dominant *detectable* failure; all three are shared-checkout collisions |
| 1.3 Step repetition (cross-session) | E3, E6 | 2/7 | both benign (caught at merge); E3 also a corroboration *win* |
| 3.3 Incorrect verification | E4, E5 | 2/7 | vacuous-pass bug; self-cert residue — **both caught by a 2nd instance** |
| 1.2 Disobey role/namespace spec | E2, E7 | 2/7 | namespace collision; provenance-file drift |
| 3.2 No/incomplete verification | E5 | 1/7 (+standing gap) | caught for promotion; **0-of-113 attestations audited** continuously |
| 2.5 Ignored other agent's input | E4 | 1/7 | reconciled via retraction |
| 2.1, 2.2, 2.6 | — | N/A | **undetectable** in our data |

**Headline:** the mode our substrate actually exhibits is **2.4-as-write/merge-collision on
the shared `main` tree** — and it recurs *after* worktree adoption (E2, E6). The verification
modes (3.2/3.3) fire but are **caught by the attestation primitive** — the strongest
demonstrated control.

---

## 6. Primitive → mode mitigation map (evidence-derived) + agree/disagree vs the brief

| Primitive | Demonstrably reduces (evidence) | Where it MISSED (evidence) |
|---|---|---|
| **Worktree isolation** | concurrent-edit *content* clobber (the E1 hunk-mix no longer recurs) | **namespace collision** E2 (`dc90a13`); **merge-time collision** E6 (`ec63b05c`: "merge INTO dirty primary tree FAILED"). Isolates *editing*, not the *shared merge target* or the *namespace*. |
| **Handoff archive** | redundant/colliding work caught at merge-review (E3 abandon-not-clobber; E4 reconciliation); append-only per-sid8 = collision-proof by construction | doesn't *force* thread resolution (§7); the *live* SESSION.json is clobbered between concurrent sessions (E4, E6) — only the *archive* is safe |
| **Multi-session / cross-model attestation** | **strongest control** — 3.2/3.3: E5 (`f0a36c40` caught builder self-cert residue), E4 (cross-session retraction), the verifier vacuous-pass fix | **standing 3.2 gap:** 0 of 113 attestations audited on a cadence; same-model correlation risk unaddressed (most attesters are Opus) |
| **`coord.py` locks** | *cannot credit from evidence* — shipped after E1–E3; **sandbox-blocked** ("lock-claim from interactive Bash FAILS, docker socket denied") | the two post-lock collisions (E2, E6) happened anyway; no handoff shows a lock *preventing* a collision → **near-zero demonstrated effect** |
| **Cooling-off (7-day)** | mechanism exists and is *used* (pins marked "in cooling-off") | **no episode shows it *catching* a premature promotion** — practiced ritual, not an evidenced save |
| **Reattestation (DETECT+ASK)** | **detects** 2.4/1.2 intent-drift (E7, 3 fires) | **advisory-only** ("never gates/reverts") — a witness, not a gate; effect on outcomes undetectable (no counterfactual) |

**Agree / disagree vs the brief's implied claims:**

- **worktree → write-collision: PARTLY DISAGREE.** Worktrees fixed the *hunk-mix* class (E1)
  but **two collision classes survive** — namespace (E2) and merge-into-dirty-tree (E6),
  both *after* adoption. Honest claim: "worktrees fixed concurrent-edit clobber, not
  shared-target or namespace collision."
- **handoff → loss-of-context: AGREE (qualified).** The *archive* preserves cross-session
  context; the *live* SESSION.json does not (clobbered).
- **attestation → incomplete-verification: AGREE (strongest-supported).** E5/E4 are clean
  positives. Caveat: the standing-audit gap + same-model correlation.
- **cooling-off → premature-promotion: UNSUPPORTED.** Not refuted — *unproven* from the
  corpus (no traced catch). Don't read "unproven" as "absent."
- **The brief's foxden example is WRONG.** It cites "the foxden v1.2 supersession of an
  independent v-branch" as a *failure*. Git shows a clean **convergent rediscovery** (a
  *success*): session `7843b781` independently rebuilt the ranker, found `main` already at
  v1.2 at merge-review, and **abandoned its branch** (`a7ef90a`) — corroborating the
  drop-the-fox verdict from an independent lineage (a decorrelated-replication win). The
  foxden line is the same-lineage, finding-driven walk-back `ad24a91`. *Refuted; corrected in
  the brief.*

---

## 7. Autonomy twist — convergence-stall under no authority

MAST's taxonomy is **principal-agent** (an orchestrator commands workers). Our topology is
**peer-contracting** (sovereign sessions, no commander; briefs are suggestions a session may
decline). The expected mode MAST *lacks*: **failure-to-converge under no authority.**

**What the traces show:**
- **68 of 107 briefs (64%) are `status: open`;** only 4 declined, 2 superseded. The directory
  is dominated by un-acted-on suggestions. 25 open briefs are >14 days old.
- **Recurring open_threads** carried unresolved across handoffs (`(carry)` ×55).

**The honesty correction (weakens the naive stall claim):** the highest-recurrence carry-threads
are **single-sid8** — e.g. `roth-video` recurs in 10 handoffs but **1 distinct session**;
`hbp-attestation` 8 handoffs, 1 session. That is **one session re-carrying its own backlog
across a marathon**, *not* peers deadlocking on shared work. The genuinely cross-session
deferrals are smaller and are all **"blocked on Blake's call."**

**Did peers ever hold incompatible canon with no one to resolve it?** The closest real case is
**E4** — `2093ac25` and `b01e5e36` held *opposite* prod-cutover plans simultaneously. It **did
not stall**: it self-converged when one session retracted, persuaded by the other's
append-only argument. Evidence the substrate *can* self-converge on a genuine incompatibility.

**But the resolution authority is consistently Blake.** All 4 declined briefs were declined by
"Blake nod"; the blocked cross-session threads are all "Blake's call."

**Verdict on the twist.** A pure peer-only failure-to-converge **does not clearly fire** in the
corpus — *because a human authority (Blake) is silently performing the force-convergence the
topology lacks.* The substrate doesn't stall **because it isn't actually authority-free.**
Remove Blake (the stated north-star of true bilateral peer autonomy) and the 64%-open backlog
+ the "blocked on Blake's call" threads suggest convergence would **not** self-organize.
→ **Weak-to-moderate evidence FOR a constitutional force-convergence mechanism**
(`multi_party_coordination_substrate`), currently substituted-for by the operator. This is
interpretive — see §8.

---

## 8. Confidence, limitations, and what a cross-model pass must re-check

**High-confidence (hard artifacts, model-independent):** the taxonomy (§2); E1/E2/E3/E6
collision facts (`584eb8d`, `dc90a13`+`a5d1dec`+`d544860`, `a7ef90a`, `ec63b05c`); brief-status
counts (68 open / 4 declined); "all 4 declines were Blake"; the foxden refutation; `coord.py`
ship date + sandbox-blocked state.

**Low-confidence — flag for cross-model recheck:**
1. **E4 "self-convergence" reading** — genuine persuasion vs deference (charity-to-same-family risk).
2. **§7 "Blake-is-the-de-facto-gate" inference** — the central twist conclusion; an
   interpretation over status fields, not a measured counterfactual.
3. **E5 "standing 3.2 gap" severity** — whether "0 audited" is a real risk or intended
   anchor-now-verify-on-demand design.
4. **All ABSENCE judgments** — no rate for 2.1/2.6 (undetectable); no cooling-off *save* found.
   **Do not read "unproven" as "absent."**

**Sample limitations:** N=7 of 227; overlapping arcs; recency skew; handoff-summary self-report
bias.

---

## 9. Consequences (follow-ons, not part of the read-only audit)

1. **Fleet-view spec sharpened.** The real recurring failure is *namespace + merge-time
   collision on the shared tree*, and locks are broken — so the `anvil_fleet_view_slice` read
   should surface **claimed paths/filenames in flight + dirty-primary-tree state**, not just
   aggregate `hololoom_locks`. (The thing that would have caught `dc90a13`.)
2. **`coord.py` lock is sandbox-blocked** — a live broken instruction in the SessionStart
   hook ("claim it: `coord.py lock claim`"). Separate small fix.
3. **Canon claims to amend** (route per the CLAUDE.md amendment procedure, do not edit
   unilaterally): the worktree section overstates collision-safety; the cooling-off
   "catches premature promotion" claim is unproven.
4. **The escape-hatch question is now empirical-ish:** the `multi_party_coordination_substrate`
   gate is currently a human (Blake). Worth a cross-model confirmation before treating §7 as
   load-bearing.

---

*Provenance: independent Opus-4.8 auditor (read-only), spine re-verified by a second Opus-4.8
instance. All claims cite a file path, sid8, commit SHA, or verbatim quote actually read.
Same-model-family caveat applies; §8 lists labels requiring a cross-model pass. Full per-episode
labels in the originating audit transcript.*
