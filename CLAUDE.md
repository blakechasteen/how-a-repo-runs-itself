# hololoom_mcp — Claude Code instructions

This repo is the unified read surface over Mythrl's knowledge stack. The point
of the project is to stop Claude Code from burning 100k+ tokens orienting in
fresh sessions — so this contract stays lean, and the protocol below is
non-negotiable for sessions in this repo *and* any Mythrl/HoloLoom work where
this server is registered.

Two halves: an **operating protocol** (what you must DO — read first) and the
**canon-emission governance** disciplines below it. Dated provenance/history for
the governance disciplines lives in `CLAUDE_HISTORY.md`, not here.

---

# Operating protocol

## Two tiers — experience vs artifact

The corpora split into two structurally different tiers, each with its own
discipline and natural graph:

- **Experience tier** (`swarm`, `sessions`): things that *happened* — voice
  memos, Matrix conversations, Claude session turns. Provenance = "who said this
  in which Matrix room when." Written by Para's bot swarm + the
  session-bobbin-materializer. Natural graph = concept × entity × room × time;
  HippoRAG-style PPR fits here and is live, **corpus-scoped to the experience
  tier**. Recall status + mechanics (scoping, testbed-suppression, coverage) are
  canonical at the PPR note under *query routing* — see there, not here.
- **Artifact tier** (`docs`, `git`, `code`): things that *got produced* — files
  committed, code parsed, docs written. Provenance = "what file at what SHA at
  what line." Written by `tools/index_*.py` from filesystem state. Natural graph
  (when one is needed) = call/citation graph, *not* HippoRAG. Currently flat
  vector indexes.

Capability is asymmetric and intentional: the experience tier gets graph
reasoning; the artifact tier stays flat unless a specific need emerges. Don't
extend HippoRAG to code/docs/git — different data shape, different algorithms.

## Session-start protocol (REQUIRED)

Before reading any source file, before answering architecture questions, before
any tool call other than these two:

1. Call `hololoom_orient` (no args, or with a `topic` hint if user gave one).
2. Read your live scratchpad if present — plain `SESSION.json` in a worktree,
   `SESSION.<sid8>.json` on the shared main checkout (#83 shape 1; see *State
   continuity*). A fresh worktree won't have one — then the previous session's
   handoff is the most-recent `handoff/sessions/*.json`, which orient surfaces as
   `related_sessions`. Continuity is work-centric, not a single live file.
3. Briefly confirm: "Oriented. Last session: <one line>." Wait for input.

Skipping (1) wastes tokens. Skipping (2) means re-explaining state. Don't.

## Worktree-per-session (REQUIRED once you'll edit files)

All Claude sessions share one git working tree on `main`; parallel sessions'
uncommitted edits collide (proven 2026-05-27; incident detail →
`CLAUDE_HISTORY.md`). The first-order fix is
isolation: each editing session owns its own checkout. **Isolation is necessary,
not sufficient** — two collision classes survive it (see the note below).

**When:** the moment a session will modify any file. Pure read / orient / Q&A
sessions can stay on `main` — no worktree overhead needed.

**How (after the session-start protocol above):**
1. Call `EnterWorktree` (branches from local `main` — `worktree.baseRef: head`
   in settings.json — into `.claude/worktrees/<name>`; switches the session in).
   No *concurrent-edit* collision: separate working directory, own branch (but
   see the surviving-collision note below).
2. From the worktree's `hololoom_mcp/`, run `bash tools/wt-venv.sh` once. `.venv`
   is gitignored so the fresh checkout lacks it; this symlinks the canonical one
   so `./.venv/bin/python` works identically.

**Runtime vs edit isolation — important:** the MCP server and launchd indexers
run off the **`main`** checkout, not your worktree. Your edits don't affect the
live services until merged. Test your changes by importing your worktree's copy
(`PYTHONPATH=. ./.venv/bin/python -c "import server; ..."`); they go live only on
merge-to-`main` + a restart of the consuming process. **That restart is NOT the
same for both: the launchd indexers need an actual reload, but the MCP server is
per-session stdio (`mcp.run()`) — each Claude session spawns its own `server.py`
from `main` at startup, so there is no shared MCP daemon to kick. New sessions
auto-serve merged code; only in-flight sessions stay stale until they reconnect.
Don't go hunting for a server to reload.** (verified 2026-06-05)

**Worktrees are necessary, not sufficient — two collision classes survive (MAST
self-audit 2026-06-19, `docs/mast_self_audit_2026-06.md`).** Isolation killed the
*concurrent-edit content* clobber, but two classes recur *under* worktrees:
1. **Namespace collision** — two sessions independently create the same new path
   (`dc90a13`: two `tools/closing_gate.py`, different tools, caught only at merge).
2. **Merge-into-dirty-tree** — merging a branch into a primary tree carrying
   another session's uncommitted edits (`ec63b05c`).
Before creating a new file or merging, check **`hololoom_fleet` →
`in_flight.contended`** (dirty paths across all worktrees) — the signal
`coord.py` locks were meant to carry but can't (lock-claim is sandbox-blocked:
`docker.sock` denied from shells).

**Merge at the boundary (at `/handoff`):** merge your branch's *code* to `main`
deliberately (review, then `git merge`). `SESSION.json` is **gitignored**
(per-worktree local scratchpad — done 2026-05-27), so it never enters a merge;
the shared cross-session record is the handoff archive (`handoff/sessions/*.json`,
unique sid8 filenames, merge-safe by construction). On session exit, the
keep/remove prompt (or `ExitWorktree`) cleans up the worktree.

## Tool budget — progressive disclosure

Narrow before fetching detail. Always.

- `hololoom_orient` (~3k tok) — once per session, at start. A `topic` that exactly names a `lens/<name>.md` pre-loads a curated **reading context** (salience pins + corpus defaults + standing-context prose) instead of the fuzzy thread/decision filter. See `conventions/lens_CONVENTION.md`.
- `hololoom_search` (~80 tok/result) — semantic, 8 corpora: swarm/sessions/docs/git/code/external/peer_bobbins/chatgpt (default `all` fans all **except** `chatgpt`. `peer_bobbins` = the P3 refusal-consent governance-audit surface; `chatgpt` = Blake's imported ChatGPT/MirrorCore history — opt-in, not in `all`/`timeline`; `swarm` = cleanly Para voice/Matrix, the import + synthetic beekeeping probes excluded.)
- `hololoom_grep` (~40 tok/match) — literal/regex across repos (when the symbol is the question)
- `hololoom_codegraph` (~40 tok/result) — Python call graph over the repos (live ast): `callers` / `callees` / `importers` for a symbol. Single-hop, name-resolved (ambiguity + `recv_match` surfaced honestly). Artifact-tier call graph — NOT HippoRAG; reflects committed repo state, not your worktree.
- `hololoom_def` (~per def) — exact symbol source: qualname → the full def read live from disk (not the 30-line `search corpus=code` preview). Returns every match when a qualname is ambiguous.
- `hololoom_navigate` (~40 tok/result) — find related results from a seed (entity-overlap or vector-near). The `query`+`via_graph=True` path runs HippoRAG PPR (corpus-scoped to the experience tier; testbed suppressed) — thin real recall or an honest `[]`. See the PPR note below.
- `hololoom_canon` (~40 tok/result) — traverse the AUTHORED `:CanonPin` citation graph (memory-pin `[[links]]` + tensions): `neighbors` / shortest-authored-`path` / `central`ity / `community` / `hygiene` / `candidate_edges` (generative: similar-but-unlinked pin pairs as authoring prompts — derived-tier suggestion, never an asserted edge). Pointer-returning, trust-tiered; manual-refresh graph, every result carries `graph_freshness`. Artifact-tier citation graph — NOT HippoRAG.
- `hololoom_resolve` (~60 tok) — uniform cross-tier address resolver: ANY handle (pin slug / sid8 / commit sha / `path:line` / `*.md` brief / Qdrant point id / `neo4j:cobs-*` observation) → `{kind, canonical_handle, tier, writer, summary, hop_menu}`. `hop_menu` = the next calls you can make from here, trust tier labeled in-band. Pointer-level — bodies stay behind `fetch`.
- `hololoom_fetch` (~500–1k tok/each) — full detail; batch IDs, sparingly
- `hololoom_timeline` (~60 tok/entry) — recent Para changelog window (Qdrant scroll over swarm_materialized; ts-sorted desc)
- `hololoom_session_state` (~small) — per-corpus freshness: point count + newest-materialized ts + a `basis` label. The mechanism *Recall freshness* (below) tells you to check. Overlaps `hololoom_fleet`'s freshness section — which supersedes which is open; use whichever is already loaded.
- `hololoom_fleet` (~per call) — coordination read: one labeled view of who's live (presence) + what's dirty/**contended** across worktrees (the namespace/merge-collision surface `locks` miss — check before editing or merging a shared file) + open briefs + recent reattestations + ready-to-ratify + corpus freshness. VIEW-only (no dispatch verb). Composes the `hololoom_presence`/`hololoom_locks` coordination primitives the SessionStart hook surfaces. (shipped 2026-06-20, `docs/mast_self_audit_2026-06.md`)

Never call `hololoom_fetch` blind. Run `search` or `navigate` first. Got an
opaque handle and not sure what it is? `resolve` it.

## Choosing a tool — query routing

| Intent | Tool |
|---|---|
| "Where did I write/discuss X?" | `search` corpus=`all` (or `sessions` if conversational) |
| "Find the function/class that does X" | `search` corpus=`code` |
| "What's our doc / canon on X?" | `search` corpus=`docs` |
| "What did we commit recently about X?" | `search` corpus=`git` |
| "Find the literal symbol/string X" | `grep` (faster + exact, no embedding round-trip) |
| "Who calls X / what does X call / what imports X?" | `codegraph` op=`callers`/`callees`/`importers` |
| "Give me the exact full source of symbol X" | `def` (qualname → live source) |
| "Voice memo / Matrix activity in scope Y" | `search` corpus=`swarm` or `timeline` (Qdrant ts-scroll) |
| "What's semantically near result Z?" | `navigate` `via_graph=False` (default — entity-overlap or vector-near) |
| "What's structurally connected to a seed Z?" | `navigate` `seed_id=…` `via_graph=True` (Yarn: file siblings for artifacts; Para's FOLLOWS / HAS_TURN for sessions) |
| "What concept has property Y / bridges to X? (multi-hop QA — answer NOT in the question's words)" | `navigate` `query=…` `via_graph=True` — the graph's niche (beats flat ~2× on 2-hop) |
| "Find passages ABOUT X (direct single-shot lookup)" | `search` `corpus=sessions` (dense workhorse — out-recalls PPR single-shot) |
| "What canon cites / is cited by pin X (+ tensions)?" | `canon` op=`neighbors` |
| "Shortest *authored* path between two canon ideas A→B?" | `canon` op=`path` |
| "Which canon is most load-bearing / what bridges clusters?" | `canon` op=`central` |
| "What's pin X's topic cluster / what tensions exist?" | `canon` op=`community` / `tensions` |
| "I have a handle (sid8 / sha / cobs-* / path:line / slug) — what is it + where can I go?" | `resolve` |
| "Pull full content for IDs [...]" | `fetch` (only after search has narrowed) |

**PPR note (canonical; corpus-scoped 2026-05-30, sid8 42979fb8).** `navigate`
with a `query` (not a `seed_id`) + `via_graph=True` routes to the HippoRAG PPR
engine, **corpus-scoped to the Mythrl experience tier** — the beekeeping/
MirrorCore testbed sharing the synonym graph is suppressed, so a Mythrl query
gets thin real recall or an honest `[]`, **never** confident off-domain hits.
**Route by query KIND (probed + replicated cross-instance + cross-model
2026-06-21):** for a *multi-hop* question whose answer concept is **not in the
question's own words** (e.g. "how is session provenance made cryptographically
unforgeable" → *session-chain / rekor*), the `query`+`via_graph` path is the
**specialist** — graph expansion bridges the vocabulary gap and beats flat ~2×
on intentional 2-hop QA. For *single-shot* "find passages about X," flat
`corpus=sessions` is the **workhorse** (it out-recalls PPR coverage-independent).
Both remain capped by the MENTIONS coverage ceiling (structural: raw turns carry no
edges; observations are near-fully covered — see
`handoff/brief/coverage_dropped_tail_dual_lever.md`). Recall is thin by *coverage*,
not plumbing — **re-probe before relying on it**: the standing decision instrument is
`tools/_cov_indep_probe.py` (+ `tools/_multihop2_probe.py` for the 2-hop specialist
claim), coverage-independent and same-day deterministic (re-characterize with
`tools/_cov_indep_variance.py`). Judge any retrieval/coverage change by **same-day
paired draws** — longitudinal deltas confound substrate growth. `tools/
ppr_canon_recall.py` is a seed-coverage/regression tripwire only; its recall@k
headline is in-pool findability at its own seed ceiling, not session recall. Dated
figures + current status live in `project_hipporag_ppr_live_over_testbed` +
`project_concept_extraction_richness`, not here. For broad session recall prefer flat
`corpus=sessions` (all turns) or `seed_id`+`via_graph` (FOLLOWS / HAS_TURN structural
nav).

**Canon-graph note (`hololoom_canon`, 2026-06-06; prose+LLM edges 2026-06-07).**
The memory pins' cross-references are materialized as a `:CanonPin` citation
graph (`tools/index_canon_graph.py`) — the *artifact* tier's natural graph, NOT
HippoRAG. **Trust-tier is never blurred — four kinds:** `authored`
(`:CITES{source:'wikilink'}`), `authored-prose` (`:CITES{source:'prose'}` — a
slug Blake wrote in prose), `extracted` (`:INVOKES`, LLM-inferred, grounded to
real slugs), `derived` (`:SIMILAR_TO`, embedder cos). Authored (wikilink+prose)
is the default; inferred tiers are opt-in via `include_derived`. Centrality is
over the authored graph; the prose layer un-distorts it (foundational pins like
`north_star` / `autonomy_thesis` are cited in prose, not `[[]]`). Results are
pointers — fetch the pin body via `search corpus=docs`. **Manually refreshed**
(one-shot `index_canon_graph.py --similar --llm`, NOT launchd), so every response
carries `graph_freshness`; re-run if `stale`. See `project_canon_pin_graph` +
the `canon_graph_query_tool` / `canon_graph_prose_edges` briefs.

Prefer a specific corpus when intent is clear. The merged `all` search is biased
toward sessions (denser prose, higher cosine) — ask `docs` for canon, `code` for
code.

### Recall freshness — check the high-water mark

Experience recall splits on **modality** (semantic/vector vs structural/graph) ×
**cadence** (realtime vs batch), and the cadence *labels lie* — a Para "realtime"
path can be staler than the batch index (verified 2026-05-26). So **never trust
the labels; check the high-water mark:**

- **Claude session turns** are **graph-only** (`:ClaudeSession`/`:ClaudeSessionTurn`,
  ts `occurred_at`; reachable via `navigate via_graph=True` from a seed, not by
  semantic search) and **not** in `swarm_materialized`. As of 2026-05-30
  `claude_hook_post_session.sh` auto-wires *every* non-bridge session →
  `#cs-<sid8>`, so the graph ingests all sessions in near-real-time — a generated
  (comprehensive) Matrix log. Still check the water mark.
  See `project_matrix_log_generated_not_curated`.
- The **only semantic index of session content** is `claude_sessions`
  (`corpus=sessions`), written by the MCP batch indexer straight off
  `~/.claude/projects/*.jsonl` (≤5 min). It depends on neither Para nor Matrix,
  so it is often the **freshest** experience channel — batch > "realtime" when
  the realtime pipeline is down.
- `corpus=swarm` carries Para bot emissions (voice/Matrix), realtime-when-healthy
  but **sparse-by-design** — an empty `timeline` is normal.

How to check: `hololoom_session_state` → `corpus_freshness` (per-corpus point
count + newest-materialized ts + a `basis` label); `timeline` returns a
`swarm_freshness` header; for graph freshness query `max(t.occurred_at)` over
`:ClaudeSessionTurn`.

## Write-path rule

**This MCP server is read-only by design.** Writers exist outside it, split
between two parties:

| Surface | Para writes | MCP indexers write |
|---|---|---|
| Qdrant | `swarm_materialized` | `claude_sessions`, `mythrl_docs`, `mythrl_git`, `mythrl_code` |
| Neo4j | `:ClaudeSession`/`Turn`/`Observation`, `:Shard`, `:Entity`, `:Concept` (HAS_TURN, FOLLOWS, MENTIONS, DERIVED_FROM_TURN, …) | `:Bobbin` meta-label + `:DocChunk`, `:Commit`, `:CodeSymbol`, `:File`, `:Repo` (IN_FILE, IN_REPO) |

Para's writers run as the bot swarm + enrichment-bot + materializer +
session-bobbin-materializer. MCP's writers are `tools/index_*.py` (Qdrant) and
`tools/yarn_writer.py` (artifact graph in Neo4j), all under launchd. `claude_sessions`
is the one misleading name: it's a filesystem mirror of `~/.claude/projects/*.jsonl`
written by MCP — same source data Para's session-bobbin-materializer reads from
Matrix-relayed events, but text-indexed independently. The two join at query time
via `turn_uuid` (see `_navigate_by_graph` in `server.py`).

If a task needs writes into the experience graph, surface it as a Para design
question — don't bypass. New artifact corpora are MCP indexer work.

Bobbin = LBP primitive (content + metadata + chain + tension). Inside the
experience tier, results may legitimately be called bobbins. Across the unified
surface, prefer "result" or "hit" — code symbols and commit subjects are not
bobbins in the LBP sense.

### Proof-block discipline (always-on)

Any verification **claim** — "tests pass," "it builds/imports," "X is wired,"
"the bug is fixed," "recall improved to N" — must carry a **Proof Block**:
`{checked: <the claim>, cmd: <exact rerunnable command>, evidence: <the actual
output you READ, not paraphrased>}`. **Mechanical-class only**: the evidence
must be reproducible from `cmd`. A free-text witness ("I reviewed it, looks
right") is **not** a Proof Block — judgment-class verification stays forgeable
until identity-keys land (`project_judgment_verify_needs_identity_keys`), so
don't dress it as proof. No Proof Block ⇒ the claim is unverified; say so
plainly rather than asserting it. Scope: claims that cross a boundary (commit /
merge / handoff / canon emission) or that a later session will rely on — not
every sentence. This makes `feedback_no_fabricated_results` structural rather
than behavioral; it is the artifact a future enforcing gate (`ritual_gate`
extension) would check.

(Ratified by Blake 2026-07-02 from `handoff/brief/claudemd_proof_block.md`,
overriding the b61fc923 reshape attestation — see the brief for the Leg-1/1b
counter-evidence and the deferral tripwire it recorded.)

## State continuity

Update your live scratchpad continuously during work — this matches the
standing per-session JSON-state preference. **Naming (#83 shape 1, Blake-
ratified at the 2026-07-02 sitting; `session_json_live_under_concurrency.md`):
in a worktree it's plain `SESSION.json`; on the shared main checkout it's
`SESSION.<sid8>.json`** (sid8 = first 8 of `$CLAUDE_CODE_SESSION_ID`) — the
shared single-slot live file was clobbered under concurrent sessions. Both are
gitignored; at session end run `/handoff`, which archives a snapshot to
`handoff/sessions/<ended>__<sid8>.json` (tracked) and deletes a spent per-sid8
scratchpad. The archive — not the live file — is the cross-session record; its
non-derivable worth is forward-intent (`open_threads` + `watch_outs`), since
code/decisions/arcs are already carried by git + context_cards + pins. Schema
is in `.claude/skills/handoff/SKILL.md`. Ratified alongside (same sitting):
verify the committed **ref**, not the shared working tree; **push your sha**,
not `main` (the tree/tip may carry a peer's unreviewed work).

### Workplan briefs (WSH — "Woosh")

`handoff/brief/*.md` are standalone markdown **workplan suggestions** proposed to
future sessions — the prospective surface between terse `open_threads` and durable
pins. A brief is a *suggestion* (LBP Tension-opener), **not a directive**: the
receiving session accepts, reshapes, or declines it. Guard that property — if
briefs become obligatory work, it's just a task queue.

`hololoom_orient` pull-surfaces `open` briefs as `workplan_briefs` (pointer only;
`Read` the file for detail). Surfacing is **topic-gated**: a brief shows on a
matching `topic` hint, or if it sets `global: true` (sparing — load-bearing
next-work only). A no-hint orient surfaces *only* global briefs.

Required frontmatter includes `done_when` — the retirement condition, **enforced**
(a brief missing it is skipped + logged, so the directory can't accumulate
open-ended briefs) — plus `interpreted_by`/`sid8` provenance. Lifecycle
`open → consumed → superseded` is a **manual** frontmatter flip, but no longer
unprompted: the `/handoff` brief-sweep (`tools/brief_sweep.py`, step 5) surfaces
retirable candidates by cheap signals and offers a safe `flip` helper. It
**surfaces, never decides** — the human confirms each flip, so the
suggestion-not-directive property holds. Full contract: `conventions/brief_CONVENTION.md`.

### Capkip (kickoff prompt)

The imperative last mile of `orient → work → handoff → woosh → capkip`. A
**capkip** is the ~5-line paste that *starts* a fresh session on work genuinely
owed to one (orient → Read brief → first safe step → order/guardrail →
done_when) — a *projection of a brief into imperative form*, not new reasoning.
It persists in the **optional** `capkip` field of the handoff
(`.claude/skills/handoff/SKILL.md`), written **only when work is owed to a fresh
session** — **never a mandatory handoff step** (that would worsen the
already-heavy ritual). Suggestion-not-directive downstream: the receiving
session may reshape or decline it (same guard as WSH). Full shape + worked
examples: `conventions/_capkip_CONVENTION.md`.

### Lenses (reading contexts)

`lens/*.md` are named, loadable **reading contexts** over the canon:
`hololoom_orient topic=<name>` pre-loads the manifest's curated pins (a *salience
spine* over MEMORY.md, not new content), default search corpora, and arc-specific
standing-context prose, and layers its declared brief topics onto the brief set.
**A lens pre-loads; it never restricts** — same suggestion-not-directive guard as
WSH briefs; if it ever *gates* what a session may read it has become an org-chart,
so pull back. No lens match → the existing fuzzy `topic` behaviour, unchanged.
Full contract + the "pins are salience, not new content" honesty:
`conventions/lens_CONVENTION.md`. See `project_lens_primitive`.

## Working preferences

- Peer/colleague tone. No over-explaining. Push back when warranted.
- Don't add features or scope without surfacing the design choice first.
- For ambiguous design questions, present 2–3 framed options, then opinion.

## Slash commands

- `/orient` — re-orient mid-session if context drifts
- `/handoff` — write session-end state to your live scratchpad + the tracked archive before exit

## Safety rails

- `.env`, `secrets/`, and `~/.claude.json` are denied via `.claude/settings.json`
- Don't run `pip install` without confirming venv activation first
- For Neo4j/Qdrant connection changes, prefer env vars over edits to `server.py`

---

# Canon-emission governance

Light-touch rules for producing canon. Full ceremony, rationale, and history
(gutted 2026-07-13 at Blake's direction — this section used to run ~170
lines) live in **`CLAUDE_HISTORY.md`**; nothing below was deleted outright.

## Memory provenance

Pins under `~/.claude/projects/-Users-blakechasteen-mythrl-dev/memory/` mark
AI-mediated content: `interpreted_by: <model-id>` when Claude writes a pin,
`originSessionId: <uuid>` pointing at the producing conversation. This keeps
AI synthesis distinguishable from Blake-authored fact — without the marker,
syntheses get read as facts and centroid collapse follows. **Set
`interpreted_by` whenever you (Claude) write a memory pin.**

## Session-signing

Sign with `<sid8>` (first 8 chars of `$CLAUDE_CODE_SESSION_ID`; fallback =
`sessionId` in the cwd-matched `~/.claude/sessions/*.json`) only when a future
session must *mechanically* disambiguate which session produced something —
parallel-session collisions, attestation provenance, cross-pin attribution.
Don't sign inline content within a single session, git commits, or memory pin
filenames — they already carry that identity.

**Format:**

| Surface | Format |
|---|---|
| Pin `originSessionId:` | `<date>__<sid8> — <descriptive context>` |
| Pin `attestations:` `session_id:` | `<date>T<HHMM>Z__<sid8>` |

## Top-of-canon pins

A pin is top-of-canon if it claims to recontextualize other pins or function
as load-bearing framing for future sessions ("READ FIRST," "supersedes,"
"settled synthesis," "sibling-tier," etc.). Before promoting one into
MEMORY.md:

- **7-day cooling-off** from creation — citable, not yet load-bearing.
- **≥1 attestation from a distinct session** (different sessionId; a
  different model is stronger — same-model agreement is weak/correlated).
- Note what it *tensions with*, not just what it agrees with — if nothing, it
  is probably a restatement of existing canon.
- **What would make it wrong.** One line. If you can't name a falsifier,
  you've written framing, not a claim — and framing that can't be wrong can't
  be corrected.

Current top-of-canon pins are listed under Architecture pointers, below.

## CLAUDE.md amendment procedure

**Factual fixes** (typos, stale pointers, broken numbers) — apply directly in
a worktree, note the fix in the commit message.

**Structural changes** (new/removed sections, a changed REQUIRED protocol, a
changed discipline) — write `handoff/brief/claudemd_<slug>.md` proposing the
diff rather than editing CLAUDE.md directly. ≥1 distinct-session attestation
— preferred form: a signed tension response
(`tools/tension_attest.py attest <brief> --verdict … --note "…"`) against a
signed proposal bobbin; ready-to-ratify computes from that signed tier where
one exists, the frontmatter `attestations:` list otherwise — plus elapsed
cooling-off surfaces the brief as ready-to-ratify at `/handoff`. **Blake
ratifies and merges.** A change Blake is directing live in-session *is* that
ratification — no separate brief/cooling-off cycle needed on top of his
direct instruction.

**Declare the class in the commit message.** `tools/claudemd_diff_gate.py`
enforces this mechanically at the push boundary (CI `governance-gates` job):
say `factual-fix`, cite the ratified `claudemd_<slug>` brief, or say
`blake-directed` for the live-direction route above. An undeclared commit
touching CLAUDE.md fails the gate — form only, it never judges the edit.

**Two tripwires, both checkable against `--tally`, neither a vibe:**
- If proposals start feeling obligatory, the suggestion-not-directive
  property is gone — pull back.
- If `blake-directed` is the only route seen in months
  (`tools/claudemd_diff_gate.py --tally --since '90 days ago'`), the
  second-opinion property is gone — push back.

## Architecture pointers

The orient brief covers all canon — do not reproduce here. Key terms to know exist
(search any unfamiliar one):

- **Substrate stack**: LBP, Headles, HoloLoom, Memory Bus, Para, Yarn, Warp,
  Navigator, Shuttle, Triton, Elle, FARM, Keep, HippoRAG. **Naming (settled
  2026-05-29):** **Autonomy** = the technical substrate stack as a noun; **Mythrl**
  = the movement / partnership claim / umbrella. See `project_autonomy_stack_name`.
- **Top-of-canon pins (the operative list; cooling-off elapsed 2026-05-18)**:
  autonomy thesis ("Autonomy all the way down"), Intelligence Tradition
  (`myth_in_mythrl`), architectural safety substrate (amended 2026-05-16 →
  `project_substrate_as_constitution`), capability-asymmetry mitigation, AI-side
  substrate primitives (TOP PRIORITY load-bearing-for-ship), Anvil (L2 team
  coordination), Packs / Ecosystems / MasterWeaver (L3 publication + install-faces),
  peer-contracting-unifies-privacy-economics (ratified 2026-06-13). When/how each
  cleared the gate → `CLAUDE_HISTORY.md`.
- **Position shift**: COZ recontextualized 2026-05-11 from "turnkey business OS
  north-star" to "substrate library shipping inside install-mode packs" (per
  `project_packs_ecosystems_architecture` + `project_anvil_team_coordination_layer`).

Memory Bus is the experience tier's underlying model. It's not the whole read
surface — that's why this MCP also exposes the artifact tier (docs/git/code),
which exists outside the Memory Bus architecture.
