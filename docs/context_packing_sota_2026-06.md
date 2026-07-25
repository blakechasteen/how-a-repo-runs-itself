# Context Packing — State of the Art (mid-2026)

> **What this is.** A cited survey of the state of the art in *context packing* — the
> inference-time discipline of assembling the optimal token payload for each LLM/agent
> call under a fixed window — as of **2026-06-19**. It is a focused **DELTA** on the
> *assembly layer* that the sibling survey
> (`agent_memory_and_context_engineering_sota_2026-06.md`) under-covers; read that one
> first for the broad field (context rot, retrieval, memory systems, the LangChain
> Write/Select/Compress/Isolate taxonomy, evaluation). Produced by the `deep-research`
> workflow: 5-angle fan-out → 23 sources → 106 extracted claims → **25 claims 3-vote
> adversarially verified (24 confirmed / 1 killed)** → synthesis; 105 agents.
>
> **Provenance.** Synthesized by `claude-opus-4-8`, session sid8 `cebf930e`, 2026-06-19.
> Artifact-tier research output, **not canon** — a snapshot of a fast-moving window, not a
> durable claim.
>
> **Disambiguation (required by scope).** This is the **context-engineering** sense —
> filling the inference window with the right tokens in the right order and cache-shape.
> It is **not** training-time *"sequence packing"* (concatenating training examples into
> one sequence to eliminate padding and raise GPU throughput). Same word, unrelated
> problem; everything below is inference-time.
>
> **Reading discipline (mirrors the parent).** *Architecture / technique* is stated as
> fact; *performance numbers* are **quarantined** and tagged **author/vendor-claimed** vs
> **independently replicated**; refuted results are flagged. The meta-finding mirrors the
> parent survey's: a **strong architectural consensus sitting on weak empirical ground** —
> every compression ratio here is author-claimed, and **none has independent third-party
> replication of the magnitude**.

---

## Thesis

The parent survey established that the field shifted from "bigger windows solve memory" to
**context engineering**. This delta drills into the step that discipline ultimately reduces
to: given a fixed budget and a pile of candidate tokens, **how do you physically assemble
the window?** Three sub-disciplines now have firm *architectural* answers:

1. **Positioning is governed by a U-shaped curve** (lost-in-the-middle): put the
   highest-value tokens at the **head and tail**, never buried mid-context.
2. **Cache-aware packing is a hard mechanical constraint, not an optimization.** All three
   major vendors reuse KV-cache only on an **exact prefix match from token 0**, which
   forces **invariant-first / volatile-last** ordering.
3. **Compression has matured into two distinct families** — extractive token-pruning
   (LLMLingua line) and latent/soft-prompt compression (gist / ICAE / xRAG).

And there is one **load-bearing tension** the parent survey never states: **cache
optimality and relevance optimality pull in opposite directions** (§3). Resolving it — by
choosing the stable-prefix / volatile-tail boundary — is the single highest-leverage knob
in context packing.

## Load-bearing takeaways

1. **Lost-in-the-middle is independently replicated and still load-bearing in 2026.** The
   U-shaped curve (primacy + recency strong, middle weak) is the empirical bedrock for
   placement. *Refinement, not refutation:* the U-shape is strongest below ~50% window
   fill; past that it shifts **recency-dominant**.
2. **KV-cache reuse = exact prefix match from the 0th token, across Anthropic, OpenAI, and
   DeepSeek** — three independent confirmations that invariant-first/volatile-last is a
   *universal* behavior, not a single-vendor quirk.
3. **The render hierarchy is `tools → system → messages`; a change at any level invalidates
   that level and everything after it.** Tool definitions are the *first* tier — so a
   volatile tool list is doubly expensive (it busts the entire cache).
4. **Cache economics are steeply asymmetric and break even fast:** cache *reads* ~0.1× base
   input (~90% cheaper), *writes* 1.25× (5-min) / 2× (1-hour); break-even at 2–3 requests.
5. **There is a silent minimum-cacheable-prefix floor.** Below it, nothing caches and **no
   error is returned** — directly bounding whether a small packed brief caches at all.
6. **Compression splits into two families with different trade-offs:** extractive
   token-pruning keeps real (interpretable) tokens at lower ratios; latent/soft-prompt
   compression reaches far higher ratios but loses interpretability.
7. **The "best format" question (XML vs markdown vs JSON) has no replicated answer** — it
   is the parent survey's named "no context-structure schema" gap. The *one* hard structural
   result is the cache hierarchy (§3), which is a formatting decision with real evidence.
8. **Progressive disclosure of tool schemas (RAG-over-tools) is the established fix** for
   tool-budget bloat — and it is exactly what this stack's `ToolSearch` deferral already
   does.

---

## 1. Token-budget allocation

**There is no independently-validated formula** for dividing a fixed window across regions
(system / tools / memory / retrieved docs / history). Allocation is a *practitioner
discipline*, not a solved theorem — surfaced honestly per the reading discipline.

What *is* primary-sourced is the budget-control **primitive** inside compression:
**LLMLingua's "budget controller"** allocates a compression budget *across prompt
components* (instruction / demonstrations / question) at **differing ratios** to preserve
semantic integrity under high overall compression (arXiv 2310.05736, EMNLP 2023). That is
the documented mechanism for spending a token budget **non-uniformly** across regions —
region-aware, priority-weighted allocation. The broader "how many tokens for retrieval vs
history vs tools" split remains an engineering choice, governed by the parent survey's
**just-in-time-over-preload** principle: keep lightweight identifiers, spend budget on
retrieved content only when needed.

## 2. In-window ordering & positioning

**The empirical bedrock — the U-shaped curve.** LLM long-context accuracy is **highest when
relevant information sits at the very beginning (primacy) or very end (recency) of the
input, and degrades significantly in the middle** — the canonical *Lost in the Middle*
result (Liu et al., **TACL 2023**, arXiv 2307.03172; Fig. 1 plots gpt-3.5-turbo on 20-doc
QA peaking ~75% at position 1, troughing ~53% mid, recovering ~63% at position 20).
**Independently replicated** across model generations including a 2026 confirmation on
1M-token models — established, not vendor-claimed.

*Qualifications (refine, do not refute):* the U-shape is strongest when the input occupies
**≤ ~50%** of the window; beyond that it shifts toward **recency-dominant / distance-based**
bias (arXiv 2508.07479, 2025), and some easy benchmarks don't surface the effect at all.
**Packing guidance derived from it is strongest when the window is not near-full.**

**Position as a first-class design variable.** LongLLMLingua (arXiv 2310.06839, ACL 2024)
names **"position bias"** as one of three co-equal long-context challenges (with compute
cost and performance reduction), equates it with lost-in-the-middle, and adds a dedicated
**document-reordering** step: reorder documents by importance score to land the best content
in primacy/recency slots. **Takeaway:** position is *actionable* — the same pass that drops
low-value tokens should also **reposition** the survivors toward the edges. Reordering
retrieved docs by relevance is an established, primary-sourced lever, not folklore.

## 3. KV-cache-aware packing (the structural constraint)

This is the section with the **hardest evidence** in the survey — three independent vendor
confirmations of the same prefix-from-zero behavior.

**Anthropic — the mechanics.** Prompt caching is a **prefix match** with a fixed render
hierarchy **`tools → system → messages`**; *"any change anywhere in the prefix invalidates
everything after it."* The operational rule: place static content (tool definitions, system
instructions, context, examples) at the **beginning**, and set the `cache_control`
breakpoint on the **last block identical across requests** — **not** on the varying suffix.
Marking the volatile block instead **silently fails to cache the stable prefix** (a cache
miss, no error). *(Live-fetched 2026-06-19 from platform.claude.com prompt-caching doc;
verbatim quotes verified 3-0.)*

**The silent minimum-prefix floor.** Below a model-specific token threshold, **nothing
caches and no error is returned.** Per the live first-party doc (live-fetched 2026-06-19,
**independently re-verified 2026-06-20**):

| Model | Min cacheable prefix (vendor-stated) |
|---|---|
| Opus 4.8 / Sonnet 4.6 / Sonnet 4.5 | **1,024** |
| Opus 4.7 | **2,048** |
| Opus 4.6 / 4.5 + Haiku 4.5 | **4,096** |
| Fable 5 / Mythos 5 | **512** |

> ⚠️ **QUARANTINE — re-verify live.** These are vendor-stated, platform-specific, and
> version-volatile. **Cross-checked two ways** (the deep-research WebFetch + an independent
> WebFetch 2026-06-20). The **bundled Claude Code `claude-api` skill table is confirmed
> STALE** — it lists Opus 4.8 = 4,096 / Sonnet 4.6 = 2,048 / Fable 5 = 2,048, all wrong vs
> the live doc above. That skill ships with the CLI and is regenerated per version, so the
> fix is **upstream, not locally patchable**. Always re-fetch the live doc before relying on
> any threshold.

**Cost economics (Anthropic; vendor-stated, definitionally not third-party-replicable —
it's a price).** Cache **reads** = **0.1× base input** (~90% savings); **writes** = **1.25×**
(5-min TTL) / **2×** (1-hour TTL); no separate caching fee. **Break-even is fast:** the
5-min TTL pays off at **2 requests** (1.25 write + 0.1 read = 1.35 < 2.0 uncached), the
1-hour TTL at **3**. This is the quantitative basis for front-loading any byte-identical
region (system prompt, tool schemas, a fixed brief) so the expensive write amortizes into
~10%-cost reads.

**OpenAI — cross-vendor convergence.** Prompt caching activates **automatically on all
eligible requests, no code changes** (opt-out-by-structure), caching the **longest prior
prefix**, hits growing in **128-token increments**. Applies only to prompts **≥ 1,024
tokens** (below that, `cached_tokens` = 0 — a hard floor; OpenAI-scoped, don't generalize
the integer). Same ordering rule as Anthropic: static first, dynamic last; **tools + images
must be byte-identical** across requests. Cost (current docs): cached input discounted
**up to 90%**, latency **up to 80%**, no extra fee. *(Cite the current docs page —
`developers.openai.com/api/docs/guides/prompt-caching` — not the Oct-2024 announcement,
whose historical text said 50%.)*

**DeepSeek — third confirmation.** Context Caching triggers a hit **only when requests share
an identical prefix starting from the 0th token**; partial mid-input matches never hit.
Same prefix-from-zero invariant as the other two.

**⟶ THE CORE TENSION (synthesis — the load-bearing insight).** **KV-cache optimality and
relevance/recency optimality pull in opposite directions.** Cache reuse demands a **frozen
prefix** (byte-identical, invariant-first, never re-ordered). But positioning (§2) and
per-query retrieval want to **re-rank and re-place** the highest-value content **per call**
— which mutates the prefix and busts the cache. The resolution the vendor docs converge on
is a **structural split**: a stable cached prefix (tools / system / instructions /
long-lived context) up front behind the breakpoint, then **all volatile, per-query,
re-ordered content (retrieved docs, recent history, the query) after it**, where
relevance-ordering is *free* because that tail is uncached anyway. **The packing designer's
real decision is the boundary:** how much context is stable enough to cache vs how much
must be re-ranked per query. That boundary is the single highest-leverage knob in
cache-aware packing.

## 4. Prompt / context compression

Two mature families. *(All ratios below are **author/vendor-claimed**; ICAE and xRAG are at
least peer-reviewed; none has independent third-party replication of the magnitude.)*

**Family A — extractive token-pruning (the LLMLingua line).** Keeps *real* (interpretable)
tokens; a small model scores importance and drops low-information tokens.

| Method | Mechanism | Claimed ratio / result | Quarantine |
|---|---|---|---|
| **LLMLingua** (2310.05736, EMNLP'23) | Coarse-to-fine: budget controller + token-level iterative pruning + distribution alignment (perplexity pruning) | **up to 20×** w/ "little loss" | Best-case — mostly **GSM8K/BBH math + GPT-3.5-Turbo**; a "compression plateau" with sharp drops **above ~20×** (arXiv 2505.00019) |
| **LongLLMLingua** (2310.06839, ACL'24) | **Question-aware** coarse-to-fine + **document reordering**; targets position bias | **NaturalQuestions +21.4%** at ~4× fewer tokens; *exceeds* the full-prompt baseline (~70.8% vs ~54.1% at the hardest doc position) | "up to" / best-position headline; GPT-3.5-Turbo, Oct-2023; raw point gain at 2× ≈ 16.7pp |
| **LLMLingua-2** (2403.12968, ACL Findings'24) | **Token classification** (keep/discard) via a Transformer **encoder** (XLM-RoBERTa-large / mBERT); **task-agnostic**, trained by **data distillation** from a GPT-4-class LLM | **2×–5×** maintaining performance | Degrades at **high ratios** and on format-sensitive agent tasks (web-shopping fails > ~30% in some setups); "maintains" holds **within** the band |

**Family B — latent / soft-prompt compression.** Compresses into *continuous learned
embeddings* (soft prompts / memory slots), not real tokens — higher ratios, **loses
human-interpretability**.

| Method | Mechanism | Claimed ratio / result | Quarantine |
|---|---|---|---|
| **Gist tokens** (2304.08467, NeurIPS'23) | Distill a prompt into a few reusable **"gist" tokens** via a **modified attention mask**; learned *for free* during instruction finetuning; **gists can be cached/reused** | **up to 26×** compression, **up to ~40% FLOPs** ↓ | A "compression bottleneck" / quality gap vs full attention on exact-recall tasks (2412.17483); verbatim-copy failures at high ratios |
| **ICAE** (2307.06945, ICLR'24) | In-Context Autoencoder: LoRA-adapted encoder (**<1% params**) → compact **memory slots** a frozen LLM conditions on directly | **~4×** on a Llama base | Paper itself: **>4× "rather challenging"**; underperforms LLMLingua-2/LongLLMLingua at 16× on 2WikiMQA/HotpotQA — 4× is the operating point, not a ceiling |
| **xRAG** (2405.13792, NeurIPS'24) | **One token per document**: reinterpret the retriever's dense **doc embedding** as a "retrieval-modality" feature, fuse via a trainable **modality bridge**; retriever + LLM **frozen** (only the bridge trains) — RAG-specific, reuses the embedding the retriever already computed | **3.53× FLOPs** ↓ (avg over 4 QA sets, ~175 tokens → 1) | Input-dependent (these 4 datasets' lengths); not independently replicated |

**The canonical family distinction (ICAE is the textbook case):** soft-prompt/latent
compression (continuous embeddings) reaches higher ratios but is opaque; extractive
token-pruning keeps real tokens and stays auditable. Pick by whether you need the packed
content to remain human/tool-readable downstream.

## 5. Structured-context schemas (the honest gap)

**There is no primary-sourced, independently-validated answer** to whether XML vs markdown
vs JSON delimiting measurably improves performance at fixed token cost. The parent survey
already records the field naming this gap: critiques of the LangChain taxonomy target what
it *omits* — **"no context-structure schema"** — not its correctness.

So the defensible state of the art is: **(a)** vendor practitioner guidance treats explicit
structural delimiting (Anthropic's own XML-tag and tool-use guidance; distinct tool/system/
content blocks) as universal good practice, but **(b)** there is **no rigorous, replicated
head-to-head** establishing a format winner with a quantified effect size. *Do not assert
"XML beats markdown."* — **confidence: medium**, reported as a gap.

The one hard, verified structural-formatting consequence: **structure that aligns with the
cache hierarchy** — tools / system / messages as distinct, stably-ordered blocks — has a
**mechanical caching payoff** (§3). That is a structure decision *with* evidence, distinct
from the unproven prose-delimiter question.

## 6. Tool / MCP packing

**Tool schemas are a first-class budget consumer that scales badly.** Every tool definition
(name, description, parameters) is packed on every call; at dozens-to-hundreds of MCP tools,
this dominates the static budget. The established mitigation is **progressive disclosure /
deferred (lazy) tool schemas — RAG-over-tools / tool-search**: expose only tool **names** (a
tiny index) plus a search/fetch tool that retrieves a tool's full JSONSchema **on demand**,
so only the tools actually needed pay their schema cost. *(Anthropic's "advanced tool use,"
"code execution with MCP," and "token-efficient tool use" engineering posts are the primary
sources; the MCP community discussion #629 tracks the pattern.)*

**Cache interaction (the multiplier).** Because tool definitions are the **first** cache
tier (`tools → system → messages`), modifying them **invalidates the entire cache**. A large
*volatile* tool list is therefore **doubly expensive** — it consumes budget *and* busts the
whole prefix when it changes. The cache-optimal *and* budget-optimal shape: a **stable,
minimal up-front tool set behind the cache breakpoint** + **on-demand schema fetch for the
long tail**.

**Tool-result management (the complementary lever).** Old, re-fetchable tool results are the
**cheapest thing to evict** — the parent survey's tool-result-clearing primitive
(`clear_tool_uses_20250919`) strips them mechanically with **no inference**, just an edit.

## 7. Relevance to Autonomy / HoloLoom

How the packing SOTA maps onto this stack's *real* surfaces. **These are design suggestions
grounded in verified findings, not measured wins — none has been A/B-tested here** (matching
the no-fabricated-results discipline).

**(1) The ~3k-token `hololoom_orient` brief.** `server.py` enforces a genuine budget
discipline: target ~3k (floor ~2,800), watcher **WARNs at 3,500 / FLAGs at 4,000**, with an
`active_threads` **cap** as the eviction lever — this *is* §1's region-aware budget
allocation, already shipped. Two cache facts bear on it:
  - *Floor:* a ~3k brief **clears the Opus 4.8 / Sonnet 4.6 floor (1,024)** but **not** the
    Opus 4.6/4.5 / Haiku 4.5 floor (4,096, quarantined). So on older models it **silently
    does not cache at all**. (This session runs on Opus 4.8 → it caches.)
  - *Ordering nuance (a correction the raw research glosses):* orient is returned as a
    **tool result in the `messages` tier**, not the system prompt. Once emitted early and
    never changed, it rides the **stable message prefix** and caches automatically on later
    turns — the caching win does **not** require reordering the brief internally. The brief's
    *internal* order matters for **lost-in-the-middle** (§2), a separate concern. The truly
    always-stable prefix worth deliberately cache-ordering is **CLAUDE.md (system) + the
    MEMORY.md spine + tool defs**.

**(2) Progressive-disclosure tool budget — already the SOTA fix.** The MCP **already defers
tool schemas via `ToolSearch`** (§6) — demonstrated live *this* session: deferred tools
appear by name only and their JSONSchema is fetched on demand before first call. The
remaining lever is making the **always-loaded core tool set stable and minimal** (so a tool
change never busts the whole prefix, since `tools` is the first cache tier) and pushing the
long tail behind on-demand fetch.

**(3) Two-tier corpora + just-in-time retrieval = the volatile tail.** Retrieved docs are
exactly the per-query content that belongs **after** the cache breakpoint, where re-ranking
is free. Apply §2 (place the best passages at primacy/recency edges) and §4 (extreme
compression) *there*.

**(4) MEMORY.md spine / catalog split = a token-budget allocation decision.** Always-loaded
spine (77 lines) vs the 58 on-demand catalog pins is structurally the **budget-controller /
progressive-disclosure pattern** (§1, §6). The spine belongs in the stable cached prefix;
the catalog is correctly JIT.

**A productive tension worth recording — the Goodhart caution.** The internal `autoresearcher`
arc *tried* to mechanically compress the orient budget and found **token-count is a Goodhart
proxy** for "does it still orient" (12% overfit, only ~1.5% generalizing, prize ~47 tokens;
line **declined** 2026-06-12). This tensions productively against §4's compression-ratio
chasing: **compress for cache/cost (mechanical, trustworthy), not for raw token-count (a
quality proxy).** It is precisely *why* the cache-ordering wins below are the right lever —
they are mechanical and carry **no quality tradeoff**, unlike compress-for-shortness.

**Worth stealing (3 concrete, each a direct application of a 3-0 finding):**

- **(a) Cache-order the stable prefix invariant-first behind one breakpoint** — CLAUDE.md +
  MEMORY.md spine + core tool schemas. Pure mechanical cost win: ~10%-cost reads on the
  stable payload across a session, **no quality tradeoff** (§3). The highest-confidence,
  lowest-risk item. **Probed 2026-06-20** (`handoff/brief/cache_order_stable_prefix.md`, 6
  sessions / 1,639 turns): already realized — **94.6% cache-read, 83.8% input-cost saved**,
  ~1.2% cold turns; the ~16–17K stable prefix reads back from turn 2 (often turn 1,
  cross-session). No CLAUDE.md/spine invalidator ⇒ **declined as already-captured**; standing
  action is just keeping the prefix volatile-free.
- **(b) Treat retrieved corpus passages as candidates for latent one-token compression
  (xRAG-style)** — the experience/artifact retrievers already produce dense embeddings, so
  *fusing them as compressed features* is the natural extreme-packing path for the
  retrieved-docs region (§4, Family B). Probe quality-retention against a
  `ppr_canon_recall.py`-style ground truth before trusting it.
- **(c) Reorder retrieved results by relevance (LongLLMLingua-style), not just drop them** —
  put the best passages at the window edges to exploit primacy/recency (§2). Improves
  accuracy, not just token count.

---

## 8. What this survey holds fixed (the deeper gaps)

This delta optimizes **within four fixed assumptions** — *one model, one window, all text,
one shot.* Each is a variable the frontier is now moving, so the largest remaining gaps are
the things held constant here. *(Reasoned gaps from known SOTA + first principles — **not**
part of the verified-claim set above; a future pass would cite them.)*

**Three frozen axes:**

1. **Time — the window is a trajectory, not a snapshot.** Real agentic runs evolve the
   window over many turns; the unsolved part is the **eviction/compaction *policy*** (what to
   drop, when to summarize, what to keep verbatim), not the primitives. The load-bearing
   interaction §3 leaves implicit: **every compaction or history rewrite is a cache-reset
   event** — so "compact rarely (keep the cache, risk rot) vs compact often (stay sharp, pay
   full price)" is a real cost/quality curve with no principled answer. The MEMORY.md
   spine/catalog split (§7) is a *static* instance of this policy.

2. **Agents — there is more than one window.** The whole survey is single-agent; packing
   *across* agents is a separate discipline: the **briefing** problem (what the orchestrator
   packs into each sub-agent), the **distillation** problem (what a sub-agent packs back —
   Anthropic's burn-50K / return-1–2K), **shared/forked cache** (can sub-agents fork the
   orchestrator's *cached* prefix rather than each paying a cold write — a large unexploited
   fan-out cost lever), and **information loss per handoff** (data-processing-inequality;
   `feedback_fan_out_only_when_write_independent` is the theory). **Probed 2026-06-20**
   (`handoff/brief/multiagent_shared_cache_probe.md`, over the 105-agent run): the
   cross-agent base-prefix *is* already cached+shared (~7.6K read by 87/105 agents) and
   caching already cuts a fan-out run's input cost **~57%** — the addressable residual is
   ~0.6%, so this specific lever is **declined as already-captured** (the harness does it;
   we don't control the breakpoint).

3. **Computation — the best packing is often *not* packing.** The frontier replaces "fit the
   data in" with "give the model a **query capability over a handle**": programmatic tool
   calling, code-execution-over-MCP, web-search dynamic filtering (filter *before* results hit
   the window). §6's tool deferral is a mild form; the MCP progressive-disclosure model is
   already "handles, not bytes," and `handoff/brief/cartridges_canon_cache_probe.md` is the
   extreme — bake the canon into a cheap KV-cache instead of re-packing the orient brief each
   session.

**Cross-cutting gaps:**

- **Exclusion is a discipline, not a fallback.** More context measurably *hurts*
  (rot / poisoning / distraction; the parent survey's LongMemEval baseline was
  distractor-confounded). Minimal-sufficient-context (Manus, Cognition) is the
  contrarian-SOTA inverse of §1–§4; the autoresearcher Goodhart note (§7) is its cautionary
  half. **Probed 2026-06-20** (`handoff/brief/retrieval_tail_packing.md`): real
  `hololoom_search` result sets are already lean — near-dup ~2% intra-corpus, **0%
  cross-corpus** over 160 slots — so content-level dedup is **declined** (existing id-dedup
  suffices).
- **Trust boundaries *inside* the window.** Packing seats untrusted content (retrieved docs,
  tool results, web pages) beside trusted instructions — the prompt-injection / "lethal
  trifecta" surface is a *packing* decision. The canon's authored/derived/interpreted
  trust-tiers + Opus 4.8's non-spoofable operator channel put this stack ahead conceptually;
  neither is wired to packing yet.
- **Cache as a *fleet* metric, not a per-request trick.** Pre-warming, hit-rate as the #1
  cost metric, cross-session shared prefixes, and TTL-as-hedge (5-min vs 1-hour = a bet on
  traffic burstiness) are the systems view §3 omits — directly relevant to 5+ concurrent
  sessions on one stable CLAUDE.md.
- **No benchmark for packing quality.** Good packing can't be told from bad except by
  end-task outcome — the same broken-eval problem as the parent survey, one level down.

**Highest-leverage to close next (this stack):** multi-agent shared-cache (axis 2) and
compute-over-context (axis 3, via the queued Cartridges probe) — both have a cheap first
probe and real cost upside. Axis 1 (lifecycle) is the deepest but least actionable today.

---

## Open questions

1. **Is the live orient brief / session actually assembled cache-first** (single
   `cache_control` breakpoint at the end of the stable prefix, before any volatile suffix)?
   Requires inspecting how the consuming session sets caching — unverified here.
2. **Which model do HoloLoom sessions run on, and does ~3k therefore cache?** On Opus 4.8 /
   Sonnet 4.6 (1,024) yes; on Opus 4.6/4.5 / Haiku 4.5 (4,096) a ~3k brief silently does
   not — so the brief may need to clear 4,096 (e.g. bundle stable canon) to cache on older
   models.
3. **Does formatting (XML vs markdown vs JSON) change accuracy at fixed budget?** No primary
   effect-size source surfaced — the parent survey's named gap. A small in-house A/B on the
   orient brief / tool descriptions could close it *locally*.
4. **What is the quality-retention curve of xRAG-style one-token compression on *this*
   stack's passages?** 3.53× is QA-dataset-specific and unreplicated; untested on
   Mythrl-domain queries — needs a probe against PPR-recall ground truth.
5. **Where is the optimal stable-prefix / volatile-tail boundary for HoloLoom sessions?**
   The single highest-leverage cache-aware-packing knob, currently implicit, not designed.
   **RESOLVED 2026-06-30 (sid8 59ceca52) → `docs/cache_stable_volatile_boundary.md`** — the
   boundary drawn explicitly (capital head / cached middle / OPEX tail) + the byte-stability
   edit-batching discipline. Closes `cache_leverage_fleet_shared_prefix.md` leg (a).

## Refuted / corrected (flagged for transparency)

- **DeepSeek "$0.014/M cached vs $0.14/M miss"** — **refuted 0-3.** Only DeepSeek's
  prefix-matching *behavior* (from token 0) is asserted; that specific price is **not**.
- **Stale cache-floor table** in the **bundled Claude Code `claude-api` skill**
  (`shared/prompt-caching.md`): it lists Opus 4.8 = 4,096 / Sonnet 4.6 = 2,048 / Fable 5 =
  2,048 — **all wrong** vs the live primary doc (1,024 / 1,024 / 512), **confirmed by an
  independent WebFetch 2026-06-20**. The skill ships with the CLI and is regenerated per
  version, so this is an **upstream** fix, not locally patchable; trust the live doc.
- **OpenAI "50%" cache discount** — historical (Oct-2024 announcement). Current docs say
  **up to 90%**; cite the docs page.

## Caveats (read before reusing any number)

- **Time-sensitivity is high.** Every vendor cache figure is fast-moving and
  version-specific; the per-model thresholds were live-fetched **2026-06-19** and
  **independently re-confirmed 2026-06-20** (the bundled `claude-api` skill table disagreed
  and is the stale one). **Re-verify against the live doc** before reuse.
- **Number quarantine.** All compression ratios (LLMLingua 20×, LongLLMLingua +21.4%,
  LLMLingua-2 2–5×, gist 26×, ICAE 4×, xRAG 3.53× FLOPs) are **author/vendor-claimed**;
  ICAE/xRAG are peer-reviewed; **none independently replicated at magnitude**. Headlines are
  "up to" / best-position (GSM8K/BBH math, GPT-3.5-Turbo, Oct-2023); independent work shows
  a compression plateau above ~20× and on format-sensitive agent tasks.
- **Positioning nuance.** The U-shape weakens past ~50% window fill (shifts
  recency-dominant) and doesn't appear on easy benchmarks — guidance from it is strongest
  when the window is not near-full.
- **Cross-vendor caution.** Thresholds, discount shapes, and cached-token terminology differ
  per provider (Anthropic 90% read + 25–100% write premium; OpenAI up-to-90% current / ~50%
  legacy, no write premium; DeepSeek ~90%). **Do not assert a uniform cross-vendor number.**
- **The HoloLoom items are design suggestions**, grounded in verified findings but **not
  measured wins on this stack.**

---

## Key sources

**In-window ordering / positioning**
- Liu et al., *Lost in the Middle* — TACL 2023, arXiv 2307.03172 (cs.stanford.edu/~nfliu/papers/lost-in-the-middle.arxiv2023.pdf)
- Recency-shift past ~50% fill — arXiv 2508.07479 · mechanistic follow-ups — arXiv 2410.05983

**KV-cache / prompt-cache-aware packing**
- Anthropic prompt caching — platform.claude.com/docs/en/build-with-claude/prompt-caching *(live-fetched 2026-06-19)*
- OpenAI prompt caching — developers.openai.com/api/docs/guides/prompt-caching (+ openai.com/index/api-prompt-caching, cookbook prompt_caching_201)
- DeepSeek context caching — api-docs.deepseek.com/news/news0802 · api-docs.deepseek.com/guides/kv_cache
- Manus, *Context Engineering for AI Agents: Lessons from Building Manus* (KV-cache-hit-rate as the #1 metric) — manus.im/blog

**Prompt / context compression**
- LLMLingua — arXiv 2310.05736 (EMNLP'23) · LongLLMLingua — arXiv 2310.06839 (ACL'24) · LLMLingua-2 — arXiv 2403.12968 (ACL Findings'24)
- Gist tokens — arXiv 2304.08467 (NeurIPS'23) · ICAE — arXiv 2307.06945 (ICLR'24) · xRAG — arXiv 2405.13792 (NeurIPS'24)
- Independent compression-plateau study — arXiv 2505.00019 · soft-vs-extractive taxonomy — arXiv 2404.01077, 2405.17062

**Tool / MCP packing**
- Anthropic *Advanced tool use* · *Code execution with MCP* · *Token-efficient tool use* — anthropic.com/engineering, docs.claude.com
- MCP progressive-disclosure discussion — github.com/orgs/modelcontextprotocol/discussions/629

**Structured context / budget (framework/practitioner)**
- Anthropic *Long context tips* · *Use XML tags* — docs.anthropic.com/en/docs/build-with-claude/prompt-engineering
- LangChain middleware (context-management built-ins) — docs.langchain.com/oss/python/langchain/middleware/built-in

**Parent survey (the broad field — read first)**
- `docs/agent_memory_and_context_engineering_sota_2026-06.md`
