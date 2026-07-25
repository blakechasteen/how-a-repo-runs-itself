# Agent Memory & Context Engineering — State of the Art (mid-2026)

> **What this is.** A cited survey of the state of the art in AI agent memory and
> context engineering as of **2026-06-18**, biased toward primary sources (papers,
> official engineering blogs, framework docs). Produced by the `deep-research`
> workflow (5-angle fan-out → fetch → 3-vote adversarial verification → synthesis;
> 107 agents) plus four follow-up research agents that closed the workflow's own
> flagged coverage gaps (named memory systems, graph retrieval, the research
> frontier, and the benchmark landscape).
>
> **Provenance.** Synthesized by `claude-opus-4-8`, session sid8 `9ddb7f6d`,
> 2026-06-18. Artifact-tier doc (Q&A research output), not canon — a snapshot of a
> fast-moving window, not a durable claim.
>
> **Reading discipline (the meta-finding).** *Architecture* (verifiable from
> docs/papers) is stated as fact; *performance numbers* are quarantined and tagged
> **author/vendor-claimed** vs **independently replicated**. The single most
> important takeaway is that memory-system **evaluation is itself untrustworthy** in
> mid-2026 — so almost every leaderboard claim is vendor-self-reported and fragile.

---

## Thesis

The field has matured past "bigger context windows will solve memory." Two findings
drive everything below:

1. **(Solid)** Long context degrades — models don't use it uniformly, and the
   *associative / multi-hop* jump rots fastest — so the discipline has shifted to
   **context engineering**: curate the minimal right tokens, externalize the rest,
   retrieve just-in-time.
2. **(Sobering)** *We cannot yet trust our own measurements.* The memory benchmarks
   are demonstrably broken, and nearly every "System X beats Y" number is
   vendor-self-reported and fragile.

So the honest state of the art is a **strong architectural consensus sitting on weak
empirical ground**: everyone agrees on the *shape* of a good memory system; nobody
has an independently-replicated lead on *performance*.

## Load-bearing takeaways

1. **"Context engineering" is now a formally defined discipline** — defined by
   Anthropic and by an academic paper (*Context Engineering 2.0*, arXiv 2510.26493)
   that grounds it as *entropy reduction*: compressing high-entropy human intent into
   low-entropy machine-consumable context. (Term popularized by Karpathy/Lütke June
   2025; Anthropic *defined* rather than *coined* it.)
2. **Context rot is real but mechanistically unexplained.** Verified across 18 models
   (Chroma) + independent replication (NoLiMa, ICML'25: 11/12 models drop below 50% of
   baseline at 32K tokens). The popular *"it's the n² attention budget"* causal story
   was **refuted** in verification — only the degradation is established.
3. **The retrieval-vs-long-context debate has tilted to retrieval/hybrid** for
   multi-hop work — but "graph beats long-context" is an *assembled* claim no single
   paper makes; the strongest reasoning models narrow the gap at a cost/latency penalty.
4. **Architecture is converging; four near-universal patterns:** LLM-driven extraction
   → external store; **invalidate/supersede, don't delete**; hybrid (vector + lexical +
   sometimes graph) retrieval; **background / off-hot-path consolidation**. Notably,
   *nobody ships true time-decay forgetting.*
5. **HippoRAG 2's central admission:** graph structure *quietly taxed simple factual
   recall below plain RAG* until they engineered it back. **Adding a graph is not free
   upside.**
6. **The benchmarks are broken.** LOCOMO's answer key is ~6.4% wrong and its LLM-judge
   accepts ~63% of deliberately-wrong answers; the *same system (Zep) scores
   84%/58%/75%* on the same benchmark depending on who runs it; a plain filesystem (74%)
   beats Mem0's reported graph variant (68.5%). Trust **cost/latency** numbers
   (mechanical) over **quality** numbers (LLM-judged).
7. **Anthropic ships three composable context primitives** with distinct cost profiles,
   plus sub-agent isolation — the most concrete production playbook in the field.
8. **The frontier is "claimed-but-not-replicated."** Sleep-time compute, Titans,
   Cartridges, memory-RL — all promising, mostly single-group; the one flagship with an
   independent reimplementation (Titans) had its headline long-context claim *fail* to
   reproduce (only the core memory module survived).

---

## 1. Context engineering as a discipline

**Definition consolidated.** Anthropic: *"the set of strategies for curating and
maintaining the optimal set of tokens during inference"* — managing the whole context
state (instructions, tools, external data, history) across multi-turn agents, vs prompt
engineering's narrower "writing instructions." Cognition calls it *"effectively the #1
job of engineers building AI agents."* The academic framing (arXiv 2510.26493) adds the
*why*: machines can't "fill in the gaps" humans do, so the work is compressing intent
into low-entropy form. It also names **self-baking** — an agent digesting its own raw
context into persistent abstractions (episodic→semantic) — as the line between *recall*
and *accumulating knowledge*.

**The canonical taxonomy (LangChain): Write / Select / Compress / Isolate** — save
context externally / pull in what's relevant / keep only essential tokens / split across
sub-agents. Reproduced everywhere by mid-2026; critiques target what it omits (no
context-structure schema), not its correctness.

**Context rot — the empirical bedrock.** Chroma's *Context Rot* (18 frontier models):
performance grows *increasingly unreliable* as input length grows, **even on trivial
tasks**, and degrades faster for *semantically* (vs lexically) oriented retrieval — which
means classic needle-in-a-haystack flatters models. Independently corroborated by NoLiMa
(arXiv 2502.05167) and the *Lost-in-the-Middle* literature. On LongMemEval, focused
~300-token context beat dumping ~113k tokens by 30–60% (this specific result passed only
2-1 in verification — the full-context baseline is mostly distractors, confounding length
with noise — but the direction is corroborated).

**Named failure modes (Drew Breunig, June 2025), useful for diagnosis:** *poisoning* (an
error enters context and gets repeatedly referenced — Google's Gemini 2.5 report shows
this in a Pokémon agent), *distraction*, *confusion* (superfluous content), *clash*
(internal contradictions).

**Just-in-time over preload, hybrid in practice.** Maintain lightweight identifiers
(paths, queries, links), load at runtime — Claude Code drops `CLAUDE.md` up front but
navigates via grep/glob just-in-time. Anthropic explicitly recommends a *hybrid* (some
upfront for speed + autonomous exploration).

## 2. What the labs actually ship (production patterns)

**Anthropic's three first-party context primitives** — the clearest production playbook,
with distinct cost profiles:

| Primitive | What it does | Cost | API id |
|---|---|---|---|
| **Compaction** | Summarize a near-full window, reinitialize from the high-fidelity summary | An extra inference step (lossy by design; maximize recall first) | `compact_20260112` |
| **Tool-result clearing** (context editing) | Mechanically strip old re-fetchable `tool_result` blocks, keep `tool_use` + reasoning | **Cheapest — no inference, just an edit** (defaults: trigger 100K, keep 3 recent) | `clear_tool_uses_20250919` |
| **Memory tool** | File-based note-taking to client-side persistent store; 6 ops (view/create/str_replace/insert/delete/rename) | Persistence outside the window; you control storage | `memory_20250818` |

(These are **beta** on the API; in-product Claude Code `/compact` is long-shipped. The
compaction "lossy" demo is an explicit n=1: peak context 335K→169K, high-level probes 3/3
preserved, deliberately-obscure probes 0/3.)

**Sub-agent context isolation** (a real architecture): specialized subagents each burn
tens of thousands of tokens but return only **1–2K-token distilled summaries** to the lead
— Anthropic reported a 90.2% improvement over single-agent Opus 4 on its research eval.
**Counterpoint:** Cognition (*Don't Build Multi-Agents*) argues against it for tasks
needing shared state / sequential reasoning (fragility, ~15× token cost). Both are right —
it's a *when*, not *whether*.

**OpenAI** ships **"dreaming"** (Dreaming V3, rolling out to Plus/Pro from **June 4
2026**): an async background process that synthesizes and ages a user's memory across past
chats (*"going to Singapore"* → *"went to Singapore in July 2026"*), enabled by a ~5×
compute cut. Striking datum: **~96% of memories are created unilaterally by the system.**
("Dreaming" is branding, *not* a claimed sleep-physiology mechanism.) ChatGPT memory =
**saved memories** (explicit, editable) + **reference chat history** (implicit recall);
dreaming keeps the latter fresh.

**Other practitioners:** Cognition's **SWE-grep** (RL-trained fast retrieval; claims agents
spend >60% of turn-1 just retrieving context); Anthropic's **Contextual Retrieval**
(prepend LLM-generated per-chunk context before embedding + BM25 → −49% failed retrievals,
−67% with reranking) — the *vector-side* counterpoint to agentic grep, reminding us both
coexist by data type.

## 3. The named memory systems

Architecture is verifiable from docs; **performance is contested (§6)**. Six systems, what
actually differs:

| System | KG? | Write path | Consolidation | Forgetting | Retrieval |
|---|---|---|---|---|---|
| **Letta** (ex-MemGPT) | No | Agent self-edits tiers (core/recall/archival memory blocks); OS-style paging | **Sleep-time agent** (background, shares memory blocks, distills "learned context") | None explicit (FIFO eviction + summarize) | Vector |
| **LangMem** (LangChain) | No | Hot-path tools *or* background manager | LLM-mediated, no fixed algorithm | Invalidation (`enable_deletes`), no decay | Vector (LangGraph Store; JSON docs by namespace) |
| **Mem0 / Mem0g** | Mem0g yes (Neo4j) | ⚠️ **Paper ≠ OSS** | **Paper:** LLM picks ADD/UPDATE/DELETE/NOOP. **OSS v3: removed it** → single-pass ADD-only + MD5 dedup | Paper: contradiction-DELETE; Mem0g marks edges invalid. OSS: none | Vector (base); graph-walk + triple embeds (Mem0g) |
| **Zep / Graphiti** | **Yes** (Neo4j) | Incremental entity+edge extraction w/ reference time | Embedding+fulltext dedup → LLM merge; community label-propagation | **Bi-temporal edge invalidation** (4 timestamps; supersede, queryable history) | **Hybrid**: cosine + BM25 + graph traversal |
| **A-MEM** | No (linked notes over Chroma) | Zettelkasten notes; LLM generates keywords/tags/links | **Memory evolution** — a new note can rewrite *existing* notes' attributes | None | Vector over attribute-enriched embeddings |
| **Cognee** | **Yes** (Kuzu default) | ECL pipeline (`add`→`cognify`→`search`); dual-write graph+vector | Graph-layer dedup (not LLM-diff) | `forget()` only (user-driven) | Hybrid, auto-routed |

**Converging:** LLM extraction + vector retrieval as universal substrate; background
consolidation becoming standard; **invalidate/supersede, not delete** wherever update logic
exists. **Divergent:** graph-native (Zep, Cognee, Mem0g) vs flat-store-with-structure
(Letta, LangMem, A-MEM); who drives consolidation (fully agentic → pipeline-deterministic);
and *how time is modeled* — only Zep treats it as first-class bi-temporal. **The trap for
builders:** Mem0's famous ADD/UPDATE/DELETE/NOOP logic is in the *paper*, not the shipping
library (v3 = single-pass ADD-only + MD5 dedup) — verify against the version you run. **The
gap nobody fills:** genuine time-decay forgetting.

## 4. Retrieval — graph and agentic

**HippoRAG 1 → 2.** v1 (NeurIPS'24, arXiv 2405.14831): hippocampal-indexing analogy — an
LLM builds an open KG, **Personalized PageRank** over it does multi-hop retrieval *in a
single step*; matches iterative IRCoT at **10–30× cheaper / 6–13× faster** (the firmest
numbers in graph-RAG). v2 (ICML'25, arXiv 2502.14802) is explicitly a *correction*:
graph-RAG had been buying multi-hop *at the cost of basic factual recall below standard
RAG*, and v2 fixes that via (1) **deeper passage integration** (passages as nodes via
"contains" edges), (2) **query-to-triple linking** replacing NER-to-node (+12.5% R@5 — the
biggest internal lever), (3) **recognition-memory triple filtering** (modest: 86.4→87.1).
Reframed as **non-parametric continual learning** (the foil is fine-tuning, *not*
long-context). Base models: Llama-3.3-70B-Instruct + NV-Embed-v2. Headline: +7 mean over
NV-Embed-v2 across factual/sense-making/associative — the *point is the direction*
(comprehensive, no longer trading one for another), not the magnitude.

Honest caveats from its own table: **v1 actually beats v2 on 2Wiki F1** (71.8 vs 71.0);
LightRAG scores are catastrophic *in the HippoRAG authors' configuration* (adversarial
framing); **no independent replication**. And a correction worth internalizing: **the
HippoRAG papers never argue against long-context** — that synthesis must be assembled from
their multi-hop wins + the separate degradation literature.

**GraphRAG and the cost-cutting wave.** Microsoft GraphRAG (arXiv 2404.16130): Leiden
community detection + pre-generated community summaries → global (map-reduce, sense-making)
vs local search; *indexing is expensive*. The 2025–26 successor wave attacks that cost:
**LazyGraphRAG** (defers all LLM use to query time; claims indexing at 0.1% of GraphRAG's,
comparable global quality at >700× lower query cost), **DRIFT**, **LightRAG** (incremental
updates), **nano-graphrag**, **PathRAG**, **KAG**, **KET-RAG** (~18% indexing cost),
**GFM-RAG** (an 8M-param graph foundation model). **The independent reality check (arXiv
2506.06331, not method authors):** graph-RAG quality gains are *"much more moderate than
reported"* under LLM-judge debiasing; their ranking put **LightRAG *below* naive RAG**.
→ **Trust cost claims (mechanical), discount quality win-rates (LLM-judged).**

**Agentic / iterative retrieval** — the shift from one-shot to retrieve-reason loops:
Self-RAG, IRCoT, FLARE, ReAct → the 2025 **RL-trained search agents** (Search-R1,
R1-Searcher, DeepResearcher). This is the Claude Code grep/glob pattern. The honest academic
read (*Is Agentic RAG worth it?*): **neither agentic nor enhanced RAG is universally
better** — agentic wins in structured domains, enhanced in broad/noisy ones.

**Reranking** — the consensus funnel: *retrieve broad (hybrid BM25+dense, ~50–100)* →
*cross-encoder rerank* → *(optional) LLM listwise rerank on the top few*. Cost/accuracy
ladder: BM25/bi-encoder → late-interaction (ColBERT/ColBERTv2/ColPali) → cross-encoder
(Cohere Rerank 3.5, Qwen3-Reranker, bge-reranker-v2-m3) → LLM listwise
(RankGPT/RankZephyr). Headline reranker numbers are almost all vendor-self-reported on
BEIR/MTEB.

**Verdict (retrieval vs long-context, multi-hop specifically):** evidence favors structured
retrieval — RULER, NoLiMa, *Context Length Alone Hurts* (perfect retrieval still drops
13.9–85% with length), and multi-hop "weakest-link" papers all show flat context can't
reliably do the associative jump, and *the bottleneck is locating evidence, not synthesizing
it*. The hedge: System-2 reasoning models narrow the gap (at cost). Pragmatic consensus is
**hybrid and routed** (Self-Route matches long-context at −65% cost), not graph-purist.

## 5. The frontier

- **Sleep-time compute** (arXiv 2504.13171, Letta/Berkeley): pre-process raw context
  *offline between queries* into a reusable state → ~5× fewer test-time tokens for equal
  accuracy, ~2.5× cheaper amortized across related queries. *Stated limit:* only helps when
  the query is *predictable from context*. Shipping as **Letta sleep-time agents**. No
  independent replication of the magnitudes.
- **Continual learning** splits on *where knowledge is written*: **non-parametric** (add to
  external store, freeze weights — HippoRAG 2's pole) vs **parametric-at-inference**
  (test-time training; In-Place TTT was an ICLR'26 oral). Experience-driven agents: Voyager
  (skill library), Reflexion (verbal self-improvement), ExpeL, Agent Workflow Memory.
- **Parametric / latent memory** (the Dec'25 survey's third "form"): **Titans** (arXiv
  2501.00663 — surprise-gated neural long-term memory at test time; **independent
  reimplementation validated the memory module but the headline long-context superiority did
  *not* robustly reproduce**), Meta **Memory Layers at Scale** (arXiv 2412.09764),
  **Cartridges / self-study** (arXiv 2506.06266 — train a small KV-cache per corpus offline;
  claims 38.6× memory / 26.4× throughput vs ICL), and the established **ROME/MEMIT**
  model-editing line — with the critical caveat that *sequential edits cause
  gradual-then-catastrophic forgetting* (arXiv 2401.07453). This is *why* durable knowledge
  still lives in external stores.
- **Memory + RL** (most concrete new thread): **Memory-R1** (arXiv 2508.19828 — RL-trains
  memory ops ADD/UPDATE/DELETE/NOOP via outcome reward) vs **DeltaMem** (arXiv 2604.01560 —
  argues outcome reward is too sparse, uses a memory-state Levenshtein-distance reward).
  Neither replicated outside its group. Plus **MemOS** (memory-as-OS, "MemCube" units with
  provenance + versioning) and **G-Memory** (multi-agent hierarchical graph memory).
- **Taxonomy shift:** two fresh surveys (arXiv 2512.13564, 2602.19320) declare the classic
  short/long-term and even episodic/semantic/procedural splits inadequate, proposing **forms
  (token-level / parametric / latent) × functions (factual / experiential / working) ×
  dynamics**.

## 6. Why none of the above is trustworthy yet (evaluation)

This is the most important and least-marketed finding. **LOCOMO** (arXiv 2402.17753):
everyone benchmarks a ~10-conversation / ~1,540-QA subset; a Penfield Labs audit found
**~6.4% of the answer key outright wrong** (99/1,540) and the stock LLM-judge accepting
**~63% of intentionally-wrong answers**; ConvoMem (arXiv 2511.10523) shows **below ~150
conversations you don't need memory/RAG at all** and a plain filesystem hits 74%.
**LongMemEval** (arXiv 2410.10813, ICLR'25) is more rigorous — 500 Qs across 5 abilities
(extraction / multi-session / temporal / knowledge-update / abstention), scalable history —
but its easy splits are near-ceiling and retrieval can proxy the score.

**LLM-as-judge fragility is quantified:** position bias (GPT-4 consistent only 65% on
answer-swap; Claude-v1 23.8% — arXiv 2306.05685), length bias (+17.3% toward longer answers
— arXiv 2407.01085), self-enhancement, trial-to-trial variance. **The canonical case:** Zep
on LOCOMO reported as **84% / 58.44% / 65.99% / 75.14%** across four runs by different
parties — a ~26-point swing from configuration and numerator/denominator conventions alone.
(Note: the circulating "arXiv 2506.06331 shows >30%/50pt judge-bias swings" figure is
*misattributed* — 2506.06331 is the GraphRAG audit; the real bias numbers come from
2306.05685 / 2406.07791 / 2407.01085.)

**The 2026 successor wave** (all verified real) — fragmenting rather than consolidating:

| Benchmark | What it adds |
|---|---|
| **Locomo-Plus** (2602.10715) | "Beyond-factual" cognitive memory — retaining/applying implicit goals & constraints |
| **MEMTRACK** (2510.01353, Patronus) | Memory + state-tracking across multi-platform tool use (Slack/Linear/Git) |
| **AMA-Bench** (2602.22769) | Fixes dialogue-bias — memory over real *agent trajectories* (6 domains) |
| **MS STATE-Bench** (blog, May'26; not arXiv) | Memory-agnostic: *does the agent improve with experience?* (450 enterprise tasks) |
| **ConvoMem** (2511.10523, Salesforce) | The ~150-conversation threshold; 75K QA, abstention + changing-facts |
| **MemoryAgentBench** (2507.05257, ICLR'26) | Retrieval + test-time learning + long-range + conflict resolution |
| **BEAM** (2510.27246, ICLR'26, *independent*) | 10M-token scale, 10 abilities, built so nothing saturates it |

**Verdict:** **no trustworthy consensus benchmark exists, and the field knows it.** A
trustworthy one needs an audited deterministic key, robust grading (not a stock LLM judge),
end-to-end answer scoring (not Recall@K), scale above ~150 conversations, full capability
coverage, contamination resistance, and a pinned reproducible protocol. Until then, memory
evaluation is fundamentally unsettled — and every leaderboard should be read as marketing.

## 7. Proven vs hyped — the honest ledger

- **Proven (independently corroborated):** context rot (the phenomenon); lost-in-the-middle
  / multi-hop degradation; retrieval beats flat long-context on cost and on multi-hop
  reliability; HippoRAG's *cost/latency* edge over iterative retrieval; LLM-judge bias; the
  benchmarks being broken.
- **Real architecture, contested performance:** all six named memory systems; GraphRAG and
  successors; HippoRAG 2's quality table (self-reported); every reranker leaderboard number.
- **Promising but single-group / unreplicated:** sleep-time-compute magnitudes; Cartridges;
  Memory Layers; memory-RL (Memory-R1/DeltaMem); MemOS; G-Memory.
- **Refuted / corrected in verification:** context rot = "n²/attention budget" (mechanism
  unproven); Mem0 "26% over OpenAI on LOCOMO"; Mem0's ADD/UPDATE/DELETE logic being in the
  *shipping library* (it's paper-only); Titans' headline long-context superiority (didn't
  reproduce; core module did); Penfield "64% of key flawed" (it's 6.4% wrong key + 63% judge
  leniency).

## 8. Relevance to Autonomy / HoloLoom

How the SOTA maps onto this stack (experience/artifact tiers, HippoRAG PPR navigator, the
Memory Bus escalation spec, the canon pin-graph, session-chain provenance):

- **HippoRAG PPR (experience tier)** is the actual frontier family, and the stack
  independently rediscovered its hardest lesson: HippoRAG 2 exists because *graph structure
  quietly degrades factual recall until engineered back* — the same finding as the canon note
  that recall is *"thin by coverage, not plumbing"* and that flat `corpus=sessions` stays the
  workhorse. **Steal:** HippoRAG 2's **query-to-triple linking** (+12.5% R@5, its biggest
  lever) and **passage-as-node "contains" edges**, both aimed at exactly that coverage gap;
  re-run `ppr_canon_recall.py` against v2's design.
- **The two-tier split (graph for experience, flat for artifacts)** is the field's central
  *divergent* axis, and the deliberate "don't extend HippoRAG to code/docs/git — different
  data shape" call is the defensible one: the evidence (incl. the 2506.06331 audit) says
  graph buys multi-hop/associative reasoning but costs indexing, complexity, *and* a
  factual-recall tax — worth it only where data shape demands it.
- **Canon pin-graph's trust-tiering is ahead of the field.** Nearly every named system
  *blurs* LLM-extracted edges with authored ones; the four-tier `authored / authored-prose /
  extracted / derived` distinction (+ the `interpreted_by` provenance discipline) is the
  separation the eval-fragility crisis says is missing. MemOS's "MemCube with provenance +
  versioning" is the field reaching for it.
- **Memory Bus escalation spec (Matryoshka shells, local→Claude escalation)** ≈ Letta's
  shipped core/recall/archival hierarchy + just-in-time retrieval. It's the one piece the
  field has *shipped* as what the stack holds as *spec* — Letta's self-editing memory-block
  model + sleep-time agents are the reference implementation to study.
- **Session-chain provenance (Ed25519 + Rekor)** solves a problem the field hasn't named:
  nobody in agent-memory does cryptographic attestation of memory writes, yet OpenAI's "96%
  of memories created unilaterally" and the eval-trust collapse both point at exactly that
  accountability gap.
- **Forgetting/decay** is the field's #1 unsolved gap — *no system ships true time-decay
  forgetting*; the universal pattern is "invalidate/supersede, don't delete," which is
  archive-don't-delete exactly. The `constipated_dissipative_structure` framing (decay as
  *attention-demotion*, bytes stay) is a thoughtful answer to an open research problem; Zep's
  **bi-temporal supersession** is the closest shipped analog.

**Three things worth stealing:** (1) HippoRAG 2's query-to-triple linking for the coverage
gap; (2) Letta's memory-block + sleep-time-agent model as the Memory Bus reference; (3)
Zep/Graphiti's bi-temporal edge model as the principled form of archive-don't-delete.

Two follow-on artifacts spun out of this survey: the `reference_memory_rl_learned_ops` pin
(the learned-write-policy frontier) and `handoff/brief/cartridges_canon_cache_probe.md` (a
probe brief for compiling the canon into a latent KV-cache).

---

## Key sources

**Context engineering / context rot**
- Anthropic, *Effective context engineering for AI agents* — anthropic.com/engineering/effective-context-engineering-for-ai-agents
- LangChain, *Context Engineering for Agents* — langchain.com/blog/context-engineering-for-agents
- *Context Engineering 2.0* — arXiv 2510.26493
- Chroma, *Context Rot* — trychroma.com/research/context-rot
- NoLiMa — arXiv 2502.05167 · RULER — arXiv 2404.06654 · *Context Length Alone Hurts* — arXiv 2510.05381 · Lost-in-the-Middle — arXiv 2307.03172
- Drew Breunig, *How Long Contexts Fail* — dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html

**Anthropic production primitives**
- Cookbook: platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools
- Context management: claude.com/blog/context-management · Memory tool: platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- Contextual Retrieval — anthropic.com/news/contextual-retrieval
- Cognition, *Don't Build Multi-Agents* — cognition.ai/blog/dont-build-multi-agents
- OpenAI, *ChatGPT memory / dreaming* — openai.com/index/chatgpt-memory-dreaming

**Memory systems**
- MemGPT/Letta — arXiv 2310.08560 · docs.letta.com · sleep-time: letta.com/blog/sleep-time-compute
- Mem0 — arXiv 2504.19413 · docs.mem0.ai
- Zep/Graphiti — arXiv 2501.13956 · github.com/getzep/graphiti
- A-MEM — arXiv 2502.12110 · LangMem — langchain.com/blog/langmem-sdk-launch · Cognee — github.com/topoteretes/cognee

**Retrieval**
- HippoRAG — arXiv 2405.14831 · HippoRAG 2 — arXiv 2502.14802 · github.com/OSU-NLP-Group/HippoRAG
- Microsoft GraphRAG — arXiv 2404.16130 · LazyGraphRAG (MS Research blog) · LightRAG — arXiv 2410.05779
- GraphRAG independent audit — arXiv 2506.06331 · Agentic RAG survey — arXiv 2501.09136
- Self-Route (retrieval vs long-context) — arXiv 2407.16833

**Frontier**
- Sleep-time compute — arXiv 2504.13171 · Titans — arXiv 2501.00663 · Titans reimpl — arXiv 2510.09551
- Memory Layers at Scale — arXiv 2412.09764 · Cartridges — arXiv 2506.06266 · ROME — arXiv 2202.05262 · MEMIT — arXiv 2210.07229 · editing-at-scale forgetting — arXiv 2401.07453
- Memory-R1 — arXiv 2508.19828 · DeltaMem — arXiv 2604.01560 · MemOS — arXiv 2507.03724 · G-Memory — arXiv 2506.07398
- Memory survey (forms/functions/dynamics) — arXiv 2512.13564 · *Anatomy of Agentic Memory* — arXiv 2602.19320

**Benchmarks**
- LOCOMO — arXiv 2402.17753 · LongMemEval — arXiv 2410.10813 · ConvoMem — arXiv 2511.10523
- Locomo-Plus — arXiv 2602.10715 · MEMTRACK — arXiv 2510.01353 · AMA-Bench — arXiv 2602.22769 · MemoryAgentBench — arXiv 2507.05257 · BEAM — arXiv 2510.27246
- Judge bias: arXiv 2306.05685 · 2406.07791 · 2407.01085
