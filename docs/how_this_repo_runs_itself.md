# How this repo runs itself

*A method essay. This document describes the operating system of a
human–AI working corpus — the protocols, not the content. Every mechanism
named here is live and has receipts; several were shaped by incidents,
which are described as they happened.*

---

## The problem this solves

A large language model session starts empty. Point one at a fifteen-month
project — thousands of files, hundreds of decisions, a dozen subsystems —
and it will spend 100,000+ tokens of context (and a lot of wall-clock)
re-deriving what the last session already knew, before doing any work.
Then the session ends and the knowledge evaporates again.

Multiply that by *parallel* sessions — several AI instances working the
same repository at once — and you also get collisions: two sessions
editing the same file, two sessions independently inventing the same
filename for different tools, one session merging into another's
uncommitted work.

This repo is the answer that grew, incident by incident, out of running
that configuration daily. The short version: **treat session knowledge as
a supply chain, not a chat log.** Orientation is a served artifact, not
re-reading. State is written down at boundaries, not remembered.
Verification is mechanical, not asserted. And every rule carries the
condition under which it would be wrong.

## Orientation is an economic problem

The first mechanism is a single MCP tool call, `orient`, that a session is
required to make before touching anything else. It returns a curated brief
— architecture map, glossary, active threads, recent decisions, infra
inventory — in about 3,000 tokens.

That's the whole trick: **100k of spelunking replaced by 3k of served
context.** The brief is maintained as part of the corpus, so its accuracy
is a maintenance obligation, not an accident. A `topic` hint filters the
thread list; a topic that names a *lens* (a curated reading-context
manifest) pre-loads a salience spine over the memory instead.

The discipline is enforced socially and structurally: the project
instructions open with "call orient first; skipping wastes tokens," and
the tool budget below it prices every other call (search ~80 tokens per
result, grep ~40, full fetch ~500–1k) so that *narrowing before fetching*
is the visible default. Progressive disclosure, priced in tokens.

## Two tiers, deliberately asymmetric

The corpus splits into two structurally different halves:

- **Experience tier** — things that *happened*: voice memos, chat-room
  conversations, AI session turns. Provenance is "who said this, in which
  room, when." Its natural graph is concept × entity × room × time, and it
  gets real graph reasoning (personalized-PageRank retrieval for
  multi-hop questions whose answer isn't in the question's words).
- **Artifact tier** — things that *got produced*: committed files, parsed
  code, written docs. Provenance is "what file, at what SHA, at what
  line." It stays flat vector indexes plus exact tools (grep, a live
  call-graph, symbol-to-source resolution), with one authored citation
  graph over the memory pins.

The asymmetry is intentional and documented as such: graph reasoning fits
conversational experience; code and docs have their own natural
structures (call graphs, citations) and get those instead. Resisting the
urge to run one retrieval hammer over everything is itself a design
decision — different data shapes, different algorithms.

A routing table maps intent to tool ("where did I discuss X" → semantic
search over sessions; "who calls X" → call graph; "the literal string X"
→ grep), because the failure mode of a rich toolset is a session using
the wrong tool expensively.

## Memory with provenance tiers

Long-lived knowledge lives in **pins** — one file, one fact, with
frontmatter. The load-bearing part is the epistemic labeling:

- **Authored** — the human wrote it. Highest trust.
- **Interpreted** — an AI synthesized it. Every AI-written pin must carry
  `interpreted_by: <model-id>` and a pointer to the producing session.
  Without the marker, syntheses get re-read as facts by later sessions,
  and the corpus converges on its own echo — *centroid collapse*.
- **Extracted / derived** — machine-inferred links (LLM-extracted
  citations, embedding similarity). Opt-in at query time, never blended
  silently into the authored graph.

Trust tier is never blurred. The citation graph over pins keeps the four
edge kinds distinct, computes centrality only over authored edges, and
labels every response with graph freshness.

Pins that claim to *recontextualize other pins* — top-of-canon framing —
face a harder gate: a 7-day cooling-off, at least one attestation from a
distinct session (a different model is stronger, since same-model
agreement is correlated), a stated tension with existing canon, and **a
named falsifier**. If you can't say what would make it wrong, you've
written framing, not a claim — and framing that can't be wrong can't be
corrected.

Falsifiers fire. One pin claimed maintenance burden would rise as the
corpus grew (a "constipated dissipative structure" needing decay as a
vent). The measurement came back flat. The pin now carries "FALSIFIER
FIRED" and a downgraded claim, in place, visibly. That is the system
working, not failing.

## The session lifecycle

A working session has a shape:

**orient → work → handoff → woosh → capkip**

- **Handoff.** At session end, a structured JSON snapshot goes to a
  tracked archive — unique per-session filename, merge-safe by
  construction. Its non-derivable value is *forward intent*: open threads
  and watch-outs. (Code and decisions are already carried by git and
  pins; what evaporates without capture is what the session was *about to
  do*.) A live per-session scratchpad exists during work but is
  gitignored; the archive, not the live file, is the cross-session
  record.
- **Woosh (workplan briefs).** Proposed future work is written as a
  standalone brief — frontmatter with provenance, a topic gate for
  surfacing, and a required `done_when`: the mechanical retirement
  condition. A brief missing `done_when` is skipped and logged, so the
  directory cannot accumulate open-ended obligations. Critically, a brief
  is a **suggestion, not a directive** — the receiving session accepts,
  reshapes, or declines it, and declines are recorded without stigma. The
  moment briefs become obligatory, the mechanism has degraded into a task
  queue, and that degradation is itself a named tripwire.
- **Capkip.** When work is genuinely owed to a fresh session, the handoff
  optionally carries a ~5-line kickoff paste: orient hint, brief to read,
  first safe step, ordering guardrail, done-condition. A projection of
  the brief into imperative form — never new reasoning, never mandatory.

The lifecycle exists because session boundaries are where knowledge dies.
Each stage converts would-be-lost state into a served artifact for the
next session.

## Parallel sessions: collisions found the hard way

All sessions initially shared one checkout. Two sessions' uncommitted
edits collided — proven by incident, not anticipated. The fix was
**worktree-per-session**: the moment a session will edit files, it takes
its own git worktree and branch, and merges back deliberately at the
session boundary.

Then a self-audit (run against MAST, a taxonomy of multi-agent failure
modes) established that **isolation is necessary but not sufficient**.
Two collision classes survive worktrees:

1. **Namespace collision** — two sessions independently create the same
   new path for different tools. Caught only at merge, by luck.
2. **Merge-into-dirty-tree** — merging a branch into a primary tree
   carrying another session's uncommitted edits.

The countermeasure is a **fleet view**: one read-only call that shows
who's live, which paths are dirty in which worktrees, and — the real
signal — which paths are *contended* (dirty in two or more places).
Sessions check it before creating files or merging. Notably, the fleet
tool deliberately has no dispatch verb: it views the fleet, it never
commands it. Adding "assign work" would quietly convert peer sessions
into subordinates, and that structural line is defended in the tool's own
docstring.

A third class surfaced later: spawned sub-agents write into the primary
tree, not the parent session's worktree — leaving debris that aborts
merges. That, too, is now a recorded feedback pin with a rule attached.

## Proof blocks: claims carry their evidence

The verification discipline, always on: any claim of the form "tests
pass," "it builds," "the bug is fixed," "recall improved to N" must carry
a **Proof Block** — `{checked, cmd, evidence}` — where `cmd` is the exact
rerunnable command and `evidence` is actual output that was read, not
paraphrased.

Scope: mechanical claims only. "I reviewed it, looks right" is *not* a
proof block, and the rules say so explicitly — judgment-class
verification stays forgeable until cryptographic identity lands, so it
must not be dressed up as proof. A claim without a proof block is stated
as unverified, plainly.

This turned a behavioral rule ("no fabricated results") into a structural
artifact a future gate can check. The distinction matters: behavioral
rules erode; artifacts can be audited.

## Governance that binds the operators

The project instructions file is itself under governance:

- **Factual fixes** (typos, stale pointers) — edit directly, note it in
  the commit message.
- **Structural changes** (new protocol, changed discipline) — write a
  proposal brief instead of editing; it needs a distinct-session
  attestation plus cooling-off before the human ratifies and merges.
- **Every commit touching the instructions must declare its class** —
  and a CI gate enforces the declaration mechanically at the push
  boundary. Form only: the gate never judges the edit, it refuses
  undeclared ones.

Two tripwires watch the governance itself, both checkable against a tally
command, neither a vibe: if proposals start feeling obligatory, the
suggestion-not-directive property is gone — pull back. If
"human-directed" is the only amendment route seen in months, the
second-opinion property is gone — push back. Governance mechanisms decay
along known axes; naming the decay condition up front is what makes the
decay detectable.

## The epistemics underneath

A few cross-cutting commitments, each earned by at least one incident:

- **The builder cannot self-verify.** An AI session's self-critique of
  its own security or architectural claims was demonstrated insufficient
  — even explicit "be honest" instruction left a false claim standing.
  Verification requires a *distinct* session, preferably a distinct
  model.
- **Verify across instances, not splits.** Single-instance replication
  is overfittable; generalization claims need cross-instance evidence.
- **Labels lie; check the high-water mark.** A "realtime" ingestion path
  was measured staler than the batch index. So freshness is never
  trusted from a label — every corpus exposes its newest-item timestamp,
  and sessions check it.
- **Judge changes by same-day paired draws.** Longitudinal retrieval
  comparisons confound the change with substrate growth; the standing
  probes are deterministic and paired.
- **Archive, don't delete** — old artifacts are archaeology — held in
  tension with a documented pressure toward attention-demotion as the
  corpus grows. The tension is recorded *as* a tension, on both pins,
  rather than resolved by fiat.

## What this adds up to

None of the individual mechanisms is exotic. What compounds is the
combination:

1. **Served orientation** makes session startup ~30× cheaper, which
   makes many small sessions viable, which makes parallelism normal.
2. **Parallelism** forced real coordination machinery — worktrees, fleet
   view, contention signals — whose failure modes were found by incident
   and pinned as rules.
3. **Provenance tiers + falsifiers** keep an AI-co-authored corpus from
   collapsing into its own echo.
4. **Suggestion-not-directive** keeps the work-proposal surface from
   degrading into a task queue — preserving the property that sessions
   (and the human) exercise judgment at every boundary.
5. **Proof blocks + governance gates** move honesty from etiquette into
   artifacts that survive the session that wrote them.

The result is a repository where a fresh AI session is productive in one
tool call, where parallel sessions coexist with named (not imagined)
collision classes, and where the record of *how the system has been
wrong* — fired falsifiers, incident postmortems, downgraded claims — is
part of the corpus, on equal footing with what it currently believes.

That last property is the one to copy first.

---

*Method essay only: this document intentionally contains no corpus
content beyond what describing the method requires. It is slice S0 of a
staged, allowlist-gated public emission; anything further ships only via
an explicit per-file manifest ratified by the human operator.*
