# Agent Harnesses — State of the Art (mid-2026)

*A fact-checked research synthesis. Compiled 2026-06-19.*

*Companion to [`agent_memory_and_context_engineering_sota_2026-06.md`](./agent_memory_and_context_engineering_sota_2026-06.md) — that doc covers the memory / context-engineering substrate; this one covers the agentic control loop, multi-agent / team orchestration, protocols, and eval / failure modes.*

---

## About this document

This is the output of two adversarial deep-research passes — one on **single/general
agent harnesses**, one on **team harnesses** (coordinating many agents + humans).
Each pass fanned out web searches across 5–6 angles, fetched ~25 primary/secondary
sources, extracted ~120 falsifiable claims, and put the top ~25 through **3-vote
adversarial verification** (a claim dies if ≥2 of 3 skeptical voters refute it).

**Read the confidence tags literally.** Only claims that survived verification are
asserted here. A short [§ Refuted](#what-the-verification-killed) section lists claims
that *failed* — several of them are widely-repeated and worth un-learning. Where the
core pass's automated final-merge degraded, findings below are reconstructed directly
from the surviving per-claim verdicts and their sources, not from memory.

**The single most important caveat, stated up front:** *compute confounding.* Most
headline "multi-agent beats single-agent" results co-occur with much higher token
spend. When compute is held equal, the advantage largely evaporates (see
[§6](#6-the-uncomfortable-result-compute-confounding)). Treat every architectural win
in this document as "architecture **and/or** more compute" unless the source
controlled for budget.

---

## Executive summary

The field has **consolidated**, and mostly away from its 2024 exuberance:

1. **The loop is boring on purpose.** Production harnesses (Claude Code being the
   reference case) are a **reactive ReAct-style tool-calling loop** — model proposes a
   tool call, harness executes, result returns, repeat — *not* an elaborate
   planner-executor. The intelligence lives in the model; the harness is scaffolding
   around it. Graph/plan-execute architectures exist but are not the default.

2. **Context management, not reasoning, is the hard engineering.** Compaction
   (summarizing history to fit the window) is now understood as **necessary but
   insufficient** for long-horizon work. The durable pattern is compaction **plus
   externalized memory** — the agent writes artifacts to disk/files that survive
   context-window resets, giving cross-window continuity.

3. **The harness is as load-bearing as the model.** Reliability is a property of the
   *harness*, not just the base model; failures are diagnosed by reading execution
   **traces**, and a meaningful share of "model failures" are actually harness-design
   failures. (The qualitative claim is solid; a specific "+15–50% from harness repair"
   number was **refuted** — see below.)

4. **Multi-agent has a settled default: hierarchical orchestrator-worker.** A manager
   decomposes work, isolated-context workers execute in parallel, the manager
   synthesizes ("map-reduce-and-manage"). **Flat peer swarms are deprioritized**
   ("mostly a distraction" — Cognition) and **shared-state peer-to-peer is avoided in
   production** (Anthropic).

5. **The decisive design rule: single-thread your writes.** Extra agents should
   contribute *intelligence* (reads, advice, verification) — not conflicting *actions*.
   Parallel writers make conflicting implicit decisions and corrupt each other's work.

6. **Multi-agent wins are real but narrow — and expensive.** They beat a single strong
   agent on **breadth-first, parallelizable, high-value** work (Anthropic's Research
   system: +90.2% on an internal eval) and **lose** on shared-context, tightly-coupled
   work like most coding. Cost: ~**15× the tokens** of a chat (vs ~4× for a single
   agent). Under **equal token budgets**, single agents match or beat multi-agent on
   multi-hop reasoning.

7. **Coordination is a first-class failure source.** The Berkeley **MAST** taxonomy
   (14 modes, 3 categories, 1,600+ traces) shows inter-agent misalignment and
   error-propagation drive failures — not just weak models. A *well-designed* MAS beats
   a poorly-designed one with the same base model.

8. **Protocols matured into governed standards.** **MCP** (Model Context Protocol) is
   the de-facto tool/context interface and has moved toward a **stateless** transport
   with a published roadmap; **A2A** (Agent2Agent) is under Linux Foundation
   governance as the agent-to-agent interop layer.

---

## 1. The core agentic loop / control architecture

**The reference architecture is a reactive ReAct loop, not a planner-executor.**
*(verified 3-0; arXiv 2604.14228, corroborated by Anthropic engineering guidance.)*
Claude Code's control architecture is "fundamentally a single reactive loop": the model
emits a tool call, the harness executes it, the observation is fed back, and the loop
repeats until the model stops. There is no separate planning module that pre-computes a
DAG of steps. This is the dominant production pattern; plan-execute and graph-structured
agents (e.g. LangGraph-style explicit state machines) are a real but minority design
choice used when control flow must be deterministic.

**Design tension — ReAct vs plan-execute vs graph:**
- **ReAct / reactive** — flexible, recovers from surprises, but can wander or loop;
  the model holds the plan implicitly in context.
- **Plan-execute** — a planner emits steps up front, an executor runs them; better for
  predictable pipelines, worse at adapting mid-task.
- **Graph agents** — explicit nodes/edges (deterministic control flow, human-auditable);
  used in orchestration frameworks where you *want* the topology fixed.

The practitioner consensus is that for open-ended work the reactive loop + a strong
model + good context engineering beats elaborate a-priori planning.

### Context & memory management

- **Compaction alone is insufficient for long-running agents.** *(3-0; Anthropic,
  "Effective harnesses for long-running agents.")* Summarizing the transcript to fit
  the window loses information that later steps need.
- **The recommended long-running architecture pairs compaction with externalized
  memory and sub-agent decomposition.** *(3-0; Anthropic.)* The agent offloads state
  out of the context window rather than relying on the window alone.
- **Cross-context-window continuity is achieved via external/persistent memory** —
  durable artifacts (files, notes, structured scratchpads) the agent writes and re-reads
  across resets. *(3-0; Anthropic.)* This is the mechanism that lets an agent run for
  hours/days past a single context window.
- **Layered compaction.** Claude Code is described as managing context through a
  multi-layer ("five-layer") compaction strategy. *(3-0, but single-source — treat the
  specific layer count as that source's characterization; arXiv 2604.14228 / Arize.)*

> **Takeaway:** "context engineering" — what goes in the window, what gets compacted,
> what gets written to durable memory — is now the central reliability lever for
> long-horizon agents, ahead of prompt wording or model choice.

### The harness-vs-model thesis

- **Agent reliability depends on the harness (runtime infrastructure), not the base
  model alone.** *(3-0; arXiv 2606.06324.)*
- **Effective harness repair requires trace-grounded diagnosis** — you fix harnesses by
  reading real execution traces, not by reasoning about them abstractly. *(3-0.)*
- ⚠️ **Refuted:** the eye-catching quantification — "repairing the harness improves
  held-out performance by **15.2%–50.0%** across four benchmarks" — was **killed 0-3**.
  The *direction* (harness matters a lot) survives; the *magnitude* did not.

---

## 2. Production coding / agent harnesses

The strongest *verified* statements here are architectural, and a striking number of
popular specifics about Claude Code's internals **failed verification** — a useful
warning about how much harness "lore" circulates without support.

**What survived:**
- Claude Code is a reactive ReAct loop with the model in the driver's seat and
  operational scaffolding around it (above).
- Anthropic's published guidance on **effective harnesses for long-running agents**
  (compaction + external memory + sub-agents) is the most concrete vendor design
  reference.

**What was refuted (do not repeat these):**
- ❌ "Only **~1.6%** of Claude Code's codebase is AI decision logic; **98.4%** is
  operational infrastructure." **Killed 0-3.** The *spirit* (harnesses are mostly plumbing)
  is defensible, but this specific viral statistic is unsupported.
- ❌ "Safety is enforced by a **seven-layer defense-in-depth** pipeline separating
  reasoning from enforcement, so a compromised model can't override sandboxing
  (vs SWE-Agent/OpenHands Docker isolation, Aider git-rollback)." **Killed 0-3.**
- ❌ "Claude Code isolates subagents via **git worktree** isolation." **Killed 1-2.**
- ❌ "Claude Code exposes **exactly four** extensibility mechanisms (MCP, plugins,
  skills, hooks)." **Killed 0-3.** (Those mechanisms exist; the closed "exactly four"
  framing did not verify.)

> **Honest read:** the *comparative* landscape (Claude Code vs Codex vs Cursor vs Devin
> vs Cline/Aider) is dominated by blog-tier sourcing and vendor marketing. The robust,
> primary-sourced facts are about **architecture patterns** (reactive loop, context
> engineering, orchestrator-worker), not about any single product's internal numbers.
> The named-product head-to-head remains an **evidence gap** (see Open Questions).

---

## 3. Multi-agent orchestration

This is where the field has consolidated hardest.

- **Anthropic's production Research system uses hierarchical orchestrator-worker** — a
  Claude Opus 4 lead delegating to parallel Claude Sonnet 4 subagents that **do not talk
  to each other** — explicitly *not* a shared-state swarm. *(3-0; Anthropic, 2025-06.)*
- **It beat single-agent Opus 4 by 90.2%** on an internal research eval. *(3-0;
  corroborated across both research passes — one of the few hard "team beats solo"
  data points.)* Caveat: non-public internal eval, breadth-first queries, and token
  usage alone explains ~80% of the variance.
- **In that design, effort scales with query complexity** — the orchestrator spawns more
  subagents for harder queries (deliberate compute allocation). *(3-0.)*
- **Token cost ~15× a chat** (vs ~4× single-agent). *(3-0.)* Multi-agent is only
  economically rational when task value is high.

**Cognition's settled position** (Walden Yan, *"Multi-Agents: What's Actually
Working,"* 2026 — successor to 2025's *"Don't Build Multi-Agents"*):
- *"Multi-agent systems work best when writes stay single-threaded and the additional
  agents contribute intelligence rather than actions."*
- Parallel writers make conflicting **implicit** decisions (style, edge cases, patterns).
- Recommended shape: **map-reduce-and-manage** (manager splits → children execute →
  manager synthesizes).
- **Unstructured peer swarms are "mostly a distraction."**
- The 2026 *"Devin can now Manage Devins"* (parallel managed Devins in isolated VMs) is
  the same pattern — isolation prevents conflicting writes rather than abandoning the
  single-writer rule.

**When multi-agent helps vs hurts** *(3-0; Anthropic, corroborated by LangChain,
Augment, Google Research):*
- ✅ **Helps:** breadth-first, parallelizable, loosely-coupled work (research, broad
  search, fan-out/verify, independent subtasks).
- ❌ **Hurts:** shared-context, tightly-dependent, sequential-stateful work — **most
  coding**, where "code changes are usually sequential and stateful" and there are few
  truly parallelizable subtasks.
- The reason parallel-subagent *coding* tools nonetheless work is that they decompose
  into **independent, isolated-context units** — confirming the mechanism rather than
  contradicting it.

**Training multi-agent systems (RL).** A recent line analyzes LLM multi-agent systems
through a **reinforcement-learning credit-assignment** lens. *(3-0; arXiv 2512.02038.)*
Key result: under a single **shared terminal team reward**, **uniform credit assignment
is suboptimal** — you can't tell which agent actually helped, which mirrors the
classic multi-agent RL credit-assignment problem and motivates per-agent reward shaping.

---

## 4. Team harnesses — coordinating fleets of agents (+ humans)

*(This section draws on the dedicated team-harness pass: 23/25 claims confirmed.)*

### Coordination as a control-passing primitive

**OpenAI's Agents SDK makes handoffs first-class.** *(3-0; canonical SDK docs.)*
- A handoff is **a tool call** — control transfer to `Refund Agent` surfaces to the LLM
  as a `transfer_to_refund_agent` tool.
- **Default is full context-sharing:** the receiving agent sees the *entire* prior
  conversation history.
- An **`input_filter` / `HandoffInputData`** mechanism lets developers restrict or
  rewrite forwarded history — this is the explicit knob on the **context-sharing vs
  context-isolation** boundary. Built-ins include `remove_all_tools` and
  `nest_handoff_history` (collapse history into a summary).

This is the concrete mechanism behind the abstract tension: *how much context does a
teammate inherit at the boundary?* The SDK ships full-sharing as default but gives you
the dial.

### Coordination topologies and their tradeoffs

The canonical mid-2026 taxonomy uses **five dimensions** — actors, types
(cooperation/competition/coopetition), structures (peer-to-peer/centralized/distributed),
strategies (role-based/model-based), coordination protocols. *(3-0; "Multi-Agent
Collaboration Mechanisms: A Survey of LLMs," 2025; corroborated by a 2025 taxonomy of
hierarchical MAS.)*

| Topology | Strength | Weakness |
|---|---|---|
| **Centralized** (hub-and-spoke / orchestrator) | Simple to design & implement | Central-node failure can collapse the system |
| **Decentralized / peer-to-peer** | Fault-tolerant — survives individual agent failure | High communication overhead |
| **Hierarchical** (orchestrator-worker, multi-level) | Low bottleneck — work distributed across levels | High complexity & latency |

These are the standard distributed-systems tradeoffs applied to LLM agents. In practice
**hierarchical orchestrator-worker is the recommended default**; centralized is fine for
small teams; flat decentralized swarms are deprioritized in production.

**Alternative topologies with measured (but bounded) gains:**
- **Blackboard / shared-workspace** — all agents read/write a common space, a dynamic
  control unit picks who acts each round. Best *average* accuracy across six
  knowledge/reasoning/math benchmarks: **+4.33% over Chain-of-Thought**, +5.02% over
  static MAS, **while spending fewer tokens** (MATH: 4.7M tokens vs 16.7M for AFlow,
  13.0M for MaAS). *(3-0, but **medium** confidence: n=1, self-interested authors;
  the related claim that the control-unit is the dominant cost driver was **refuted**
  1-2.)*
- **Structured multi-model voting/consensus** — async propose/vote with dynamic restart
  → majority-vote consensus → winning agent synthesizes. A 4-model panel (Gemini 2.5
  Pro, GPT-5, Grok 4, Claude Sonnet 4) beat the **best single model on average** (81.2
  vs 80.5) — **but the lift is statistically insignificant** (McNemar p =
  0.359/0.795/0.934), and consensus leaves big headroom: ≥1 agent was correct in 95.5%
  of GPQA-Diamond cases while consensus reached only 87.4%. *(medium confidence —
  the win is real-but-not-significant and may be a compute artifact.)*

### Shared memory / context substrates — the central tension

The governing tension is **context-sharing vs context-isolation**. The verified
practitioner consensus lands firmly on the **isolation** side for *write* work:

- ❌ **Refuted (0-3):** "maximize shared context across all agents so they stay on the
  same page." The practitioner consensus is the **opposite** — isolate worker contexts,
  single-thread writes, share *results* not *working state*.
- Anthropic's design has subagents that **never communicate directly**; the orchestrator
  is the join point.
- The handoff `input_filter` exists precisely to *narrow* what context crosses the
  boundary.

Memory substrates in play: shared scratchpads / blackboards (shared-workspace topology),
message buses, and vector/graph memory for cross-session recall. The durable principle:
**share artifacts and conclusions, isolate reasoning state.**

### Human-in-the-loop fleet management

This is the **weakest-evidenced** area. The directional signals exist — Cognition's
"Devin manages Devins" (a human directs a manager-agent that directs worker-agents in
isolated VMs), parallel-subagent coding tools, agent-team dashboards — but **no
primary-source claim about concrete fleet-management control-surface tradeoffs**
(approval gates, async handoff UX, intervention-across-N-sessions) survived
verification. Microsoft's **Magentic-UI** (human-centered web agent) and the **Microsoft
Agent Framework** are named ecosystem moves but weren't reduced to verified design
claims here. **Treat "how to manage a fleet of agents" as an open, under-documented
frontier** rather than a solved pattern.

---

## 5. Protocols & interoperability

- **MCP (Model Context Protocol) is the de-facto tool/context interface**, and the spec
  has moved toward a **stateless** transport. *(3-0; modelcontextprotocol.io. Note: the
  cited revision is a forward-dated release-candidate post — treat the "stateless"
  *direction* as solid and the exact dated revision as provisional.)* Statelessness
  matters because it makes MCP servers horizontally scalable and serverless-friendly,
  vs. the original session-bound connection model.
- **The MCP 2026 roadmap is organized around four priorities.** *(3-0.)* (The roadmap
  exists and is published; the four-priority structure verified even though this
  document doesn't assert the exact four beyond the source.)
- **A2A (Agent2Agent) is under Linux Foundation governance.** *(fetched primary source;
  not independently re-verified in the confirmed set — medium confidence.)* A2A is the
  agent-to-agent interop layer (capability discovery, task delegation between agents
  from different vendors), complementary to MCP's agent-to-tool layer. Mental model:
  **MCP = agent↔tools, A2A = agent↔agent.**

> **Design note:** the protocol stack is bifurcating cleanly — a *vertical* interface
> (MCP, agent to its tools/data) and a *horizontal* one (A2A, agent to peer agents).
> Both are now multi-vendor and governed rather than single-company specs.

---

## 6. The uncomfortable result: compute confounding

This is the most important intellectual development in the field, and it cuts against
most of the marketing.

**Under equal thinking-token budgets, single-agent systems consistently match or
outperform multi-agent systems on multi-hop reasoning — while using far fewer tokens.**
*(3-0; Tran & Kiela, arXiv 2604.02460, April 2026 — tested across Qwen3-30B,
DeepSeek-R1-Distill-Llama-70B, and Gemini 2.5, on FRAMES and MuSiQue, against 5 MAS
architectures.)*

- Verbatim: *"SAS [single-agent] consistently match or outperform MAS on multi-hop
  reasoning tasks when reasoning tokens are held constant... many reported MAS gains are
  better explained by compute and context effects than by inherent architectural
  superiority."*
- Grounded in the **Data Processing Inequality**: each agent handoff can only *lose*
  information, never add it.
- Corroborated: a single agent with strong prompts ≈ the best multi-agent discussion
  approach (Wang et al. 2024); follow-up *"The Illusion of Multi-Agent Advantage"*
  (2026) extends the result.
- **Anthropic's own data** says token usage explains **~80%** of its multi-agent win.

**Scope limits (don't over-read this):** the equal-budget result is **multi-hop QA
only** — it excludes tool use, code execution, vision, and production orchestration. MAS
becomes competitive under heavy context degradation. So the honest synthesis is:
*multi-agent structure earns its keep when the task is genuinely parallelizable or when
a single context can't hold the work — not as a generic accuracy upgrade.*

---

## 7. Evaluation, reliability, safety, failure modes

### MAST — the failure taxonomy (the load-bearing eval result)

*"Why Do Multi-Agent LLM Systems Fail?"* (Cemri, Pan et al., UC Berkeley; NeurIPS 2025
Datasets & Benchmarks). *(3-0, corroborated across both passes.)*
- **14 failure modes** in **3 categories**: system-design issues (~44%), inter-agent
  misalignment (~32%), task verification (~24%) — across **1,600+ annotated traces** from
  7 frameworks, inter-annotator κ = 0.88.
- **Failure is organizational, not just model-weakness:** *"a well-designed MAS can
  result in performance gain... improvements in the base model capabilities will be
  insufficient."* System-design interventions yielded up to **+15.6%** with the **same
  base model**.
- **Error propagation is a named, distinct mode:** infinite conversation loops, amplified
  / cascading hallucinations — one agent's failure contaminates the whole system. *(3-0;
  corroborated by a deep-research-agent survey.)*

### Eval harnesses are themselves in flux

- **OpenAI published "why we no longer evaluate SWE-bench Verified."** *(primary source,
  fetched; not in the independently-confirmed set — medium confidence.)* Signal: the
  field is outgrowing its flagship coding benchmark as scaffolding/contamination effects
  make scores hard to attribute to model capability — the **benchmark-vs-scaffolding**
  attribution problem.
- The broader pattern: a model's score is a property of **model × harness × benchmark**,
  not the model alone — which is why "harness repair" and "trace-grounded diagnosis"
  (§1) are now first-class eval activities.

### Safety / sandboxing — handle with care

The verified record here is **thin**, and the most-cited specifics **failed**:
- The "seven-layer defense-in-depth / reasoning-enforcement separation" architecture
  claim for Claude Code was **refuted 0-3**.
- Common *patterns* — container/Docker isolation (SWE-Agent, OpenHands), git-checkpoint
  rollback (Aider), permission-gated tool execution, sandboxed shells — are real and
  widely used, but in this research they appeared bundled inside a refuted claim, so
  treat them as **general practice, not independently verified here.** The trustworthy
  high-level statement: production harnesses gate side-effecting actions (filesystem,
  network, shell) behind isolation + permissioning, and the specific multi-layer counts
  cited in blog posts should be distrusted absent primary sources.

---

## What the verification killed

Faithful research means publishing the corpse list. These claims were **refuted** and
should not be propagated:

| Refuted claim | Vote | Why it matters |
|---|---|---|
| "~1.6% AI logic / 98.4% infrastructure in Claude Code" | 0-3 | Viral stat, unsupported |
| "Seven-layer defense-in-depth safety pipeline (Claude Code)" | 0-3 | Specific safety architecture unverified |
| "Subagents isolated via git worktrees (Claude Code)" | 1-2 | Mechanism unconfirmed |
| "Exactly four extensibility mechanisms (MCP/plugins/skills/hooks)" | 0-3 | Closed enumeration unverified |
| "Harness repair → +15.2–50.0% on held-out benchmarks" | 0-3 | Direction OK, magnitude unsupported |
| "Maximize shared context across all agents" (team pass) | 0-3 | **Opposite** of practitioner consensus — isolate writes |
| "Blackboard control-unit is the dominant cost driver" (team pass) | 1-2 | Ablation claim didn't hold |

---

## Cross-cutting design principles (the durable takeaways)

1. **Keep the loop simple; invest in context engineering.** Reactive ReAct + strong
   model + disciplined context management beats elaborate planning machinery.
2. **Compaction + externalized memory.** Don't rely on the context window alone for
   long-horizon work; write durable artifacts.
3. **Single-thread writes; parallelize reads.** Extra agents add intelligence, not
   conflicting actions. This one rule explains most of the multi-agent guidance.
4. **Hierarchical orchestrator-worker is the default team shape.** Map-reduce-and-manage.
   Avoid flat swarms and shared-state peer-to-peer in production.
5. **Isolate worker context; share results, not working state.** The handoff boundary is
   where you tune this; default-full-sharing SDKs give you a filter — use it.
6. **Reach for multi-agent only when the task is parallelizable or exceeds one context —
   and the value justifies ~15× tokens.** Otherwise a single strong agent under equal
   compute usually wins.
7. **Treat coordination as a failure surface.** Budget for inter-agent misalignment and
   error propagation; design verification/synthesis steps, not just generators.
8. **Distrust harness lore.** A remarkable fraction of widely-cited harness "facts"
   failed verification. Demand primary sources for internal-architecture and
   percentage claims.

---

## Open questions / evidence gaps

1. **Named-product head-to-head.** Direct, matched-budget comparisons among Claude Code,
   Codex, Cursor, Devin, Cline/Aider — and among CrewAI / AutoGen(AG2) / LangGraph /
   MetaGPT / Magentic — did **not** survive as primary-sourced claims. The comparative
   product landscape is still blog-and-marketing-dominated.
2. **Human fleet-management surfaces.** Concrete tradeoffs for directing/reviewing/
   intervening across many concurrent agents (approval gates, async handoff, fleet
   dashboards) are under-documented with hard evidence.
3. **Where exactly does multi-agent structure beat single-agent *at equal compute*?**
   Tran-Kiela concede MAS becomes competitive under heavy context degradation but defer
   the crossover regime. The boundary between "just more compute" and "genuinely needs
   decomposition" is unresolved.
4. **Market/auction coordination topologies** produced no surviving evidence — whether
   bidding/market mechanisms ever beat orchestrator-worker or blackboard is uncovered.

---

## Sources

**Confidence legend:** primary = vendor engineering post / canonical docs / peer-reviewed
paper; secondary = reputable analysis; blog = practitioner/opinion.

### Core agent-harness pass
- **Anthropic — Effective harnesses for long-running agents** (primary) ·
  anthropic.com/engineering/effective-harnesses-for-long-running-agents
- **Anthropic — Building a multi-agent research system** (primary) ·
  anthropic.com/engineering/multi-agent-research-system *(and /built-multi-agent-research-system)*
- **Claude Code architecture analysis** (primary, arXiv 2604.14228) — *several specific
  claims refuted; the reactive-loop characterization survived*
- **Harness-repair / runtime-infrastructure reliability** (primary, arXiv 2606.06324) —
  *qualitative survived, the +15–50% magnitude refuted*
- **Multi-agent RL credit assignment** (primary, arXiv 2512.02038)
- **Deep-research-agent survey** (primary, arXiv 2509.16941 / 2511.19933 / 2509.09677)
- **MCP — 2026 release candidate & roadmap** (primary) · blog.modelcontextprotocol.io
- **A2A — Linux Foundation launch** (primary) · linuxfoundation.org
- **Agent protocols survey** (primary, arXiv 2505.02279)
- **OpenAI — Why we no longer evaluate SWE-bench Verified** (primary) · openai.com
- **MAST failure taxonomy** (primary) · github.com/multi-agent-systems-failure-taxonomy/MAST
- Multi-agent orchestration patterns (primary, arXiv 2605.02801); ZenML LLMOps DB;
  LangChain "How and when to build multi-agent systems" (blog); Arize context-management
  (blog); Zartis compounding-errors (secondary); SWE-bench-vs-scaffolding analysis
  (secondary).

### Team-harness pass
- **Cognition — Multi-Agents: What's Actually Working** + **Don't Build Multi-Agents**
  (primary) · cognition.ai/blog
- **Anthropic — Multi-agent research system** (primary)
- **OpenAI Agents SDK — Handoffs docs** (primary) · openai.github.io/openai-agents-python/handoffs
- **MAST — "Why Do Multi-Agent LLM Systems Fail?"** (primary, arXiv 2503.13657)
- **Equal-budget single-vs-multi study** (primary, arXiv 2604.02460); **"Illusion of
  Multi-Agent Advantage"** (arXiv 2606.13003)
- **"Beyond the Strongest LLM" — multi-model voting** (primary, arXiv 2509.23537)
- **Blackboard-architecture MAS** (primary, arXiv 2507.01701)
- **Multi-Agent Collaboration Mechanisms: A Survey** (primary, arXiv 2501.06322);
  **Taxonomy of Hierarchical MAS** (arXiv 2508.12683); Wang et al. (arXiv 2402.18272)
- **Claude Code — Agent Teams docs** (primary) · code.claude.com/docs/en/agent-teams
- **Microsoft — Agent Framework** & **Magentic-UI** (primary) · microsoft.com / devblogs
- Mem0 / Graphlit / xTrace agent-memory surveys (blog); LangGraph supervisor-vs-swarm,
  Augment single-vs-multi, framework comparison matrices (blog); Cognition-vs-Anthropic
  roundup (secondary).

---

## Methodology & honest limitations

- **Two passes**, ~215 subagent calls total, ~50 sources fetched, ~250 claims extracted,
  50 put through 3-vote adversarial verification (43 confirmed, 7 killed).
- **Reconstruction note:** the core pass's automated final-merge degraded; its findings
  above are rebuilt from the surviving per-claim verdicts and source map (not
  re-synthesized by an unverified step). Where a claim is single-source or its automated
  merge was lossy, it's flagged.
- **Forward-dated sources:** the live web surfaced a few sources dated slightly ahead of
  the compile date (e.g. an MCP RC post); their *direction* is reported, exact dated
  revisions flagged as provisional.
- **The dominant caveat remains compute confounding** — re-read §6 before citing any
  "multi-agent beats single-agent" figure.
