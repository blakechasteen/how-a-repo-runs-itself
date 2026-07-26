# hololoom_mcp

MCP server providing a unified read surface over Mythrl's knowledge stack —
Para's experience tier (swarm + Claude sessions) plus a filesystem-mirroring
artifact tier (docs / git / code) — exposed to Claude Code, with a
project-level handoff layer that kills cold-start orientation flights.

**Problem solved.** Fresh Claude Code sessions no longer eat 100k+ tokens
orienting to the Mythrl stack. They call `hololoom_orient` once (~3k tokens),
read `SESSION.json` for last-session continuity, and proceed grounded.

## Repo layout

```
hololoom_mcp/
├── server.py                  # FastMCP server, 9 read-only tools
├── context_cards.json         # Canon layer — durable architecture/decisions
├── SESSION.json               # Volatile layer — per-session continuity
├── CLAUDE.md                  # Auto-loaded by Claude Code every session
├── .mcp.json                  # Registers hololoom MCP at project scope
├── tools/
│   ├── repos.json             # Repo paths consumed by indexers + grep
│   ├── index_sessions.py      # Claude transcripts → claude_sessions (Qdrant)
│   ├── index_docs.py          # Markdown + structured docs → mythrl_docs
│   ├── index_git.py           # Commit messages → mythrl_git
│   ├── index_code.py          # Python symbols → mythrl_code
│   └── yarn_writer.py         # docs/git/code → :Bobbin artifact graph (Neo4j)
├── launchd/
│   ├── com.mythrl.hololoom.session_indexer.plist
│   ├── com.mythrl.hololoom.docs_indexer.plist
│   ├── com.mythrl.hololoom.git_indexer.plist
│   ├── com.mythrl.hololoom.code_indexer.plist
│   └── com.mythrl.hololoom.yarn_writer.plist
├── .gitignore
├── README.md
└── .claude/
    ├── settings.json          # Secrets denylist, bash allowlist
    └── skills/
        ├── orient/SKILL.md    # /orient slash skill
        └── handoff/SKILL.md   # /handoff slash skill
```

## Background writers (launchd)

Five user-level launchd agents keep the corpora fresh. Four index Qdrant
(sessions / docs / git / code); one (`yarn_writer`) projects the
docs/git/code corpora into a parallel `:Bobbin` graph in Neo4j. Each is
idempotent (deterministic UUIDv5 + skip-by-existing-ID; yarn_writer uses
MERGE), niced to 5, runs every 30 min. Logs at `/tmp/hololoom_*.{out,err}`.

```bash
# Install / load all five
for plist in launchd/*.plist; do
  cp "$plist" ~/Library/LaunchAgents/
  launchctl load -w ~/Library/LaunchAgents/$(basename "$plist")
done

# Disable temporarily
launchctl unload ~/Library/LaunchAgents/com.mythrl.hololoom.<name>.plist

# Force a manual run
launchctl kickstart -k gui/$(id -u)/com.mythrl.hololoom.<name>
```

Stagger: code indexer fires at `:07`/`:37`, yarn_writer at `:12`/`:42`,
the other three at `:00`/`:30` (drift from `StartInterval=1800`). Avoids
hammering the shared `:8765` embedding service. After editing any plist,
copy → unload → load to apply.

## Matrix changelog (optional, artifact tier)

Each artifact-tier indexer (`docs`, `git`, `code`) can post a digest to a
dedicated Matrix room when it indexes new content. **Filesystem stays the
source of truth** — git/JSONL remains authoritative; the Matrix post is
observational. The notifier no-ops silently when unconfigured.

```bash
# 1. Create bot account on Synapse (one-time, via Synapse admin)
#    register_new_matrix_user -u hololoom-mcp -p <pw> --no-admin <url>

# 2. Stash access token (chmod 600)
mkdir -p ~/.config/mythrl/hololoom-mcp
echo 'syt_...' > ~/.config/mythrl/hololoom-mcp/access_token
chmod 600 ~/.config/mythrl/hololoom-mcp/access_token

# 3. Create three rooms and invite @hololoom-mcp:
#    #hololoom-docs:chat.mythrl.ai
#    #hololoom-git:chat.mythrl.ai
#    #hololoom-code:chat.mythrl.ai
```

Add to each artifact-tier plist's `EnvironmentVariables`:

```xml
<key>HOLOLOOM_MATRIX_HOMESERVER</key><string>http://localhost:8008</string>
<key>HOLOLOOM_MATRIX_USER</key><string>@hololoom-mcp:chat.mythrl.ai</string>
```

`HOLOLOOM_MATRIX_TOKEN_FILE` defaults to
`~/.config/mythrl/hololoom-mcp/access_token`. Per-corpus room overrides:
`HOLOLOOM_DOCS_ROOM`, `HOLOLOOM_GIT_ROOM`, `HOLOLOOM_CODE_ROOM`.

A run posts only when `new > 0` (no-op runs stay silent). Sample:

```
💾 hololoom_mcp · git_indexer · +3 new commits
  • mythrl-dev a0dd7f1 livekit: self-hosted Element Call SFU
  • mythrl-dev 29941d0 hygiene: gitignore .bak rotations
  • para-bots 3a5540a Phase 3A+3B foundation: MaterializerBridge
```

Failures log to stderr and never block indexing.

## MCP tools

| Tool | Purpose | Cost |
|---|---|---|
| `hololoom_orient` | Curated session-start brief — call FIRST | ~3k total |
| `hololoom_session_state` | Derived view of SESSION.json + per-corpus freshness high-water marks | ~variable |
| `hololoom_search` | Semantic search across 5 corpora (default merges all) | ~80/result |
| `hololoom_grep` | Literal/regex across configured repos (Python `re`) | ~40/match |
| `hololoom_navigate` | Related results from a seed (entity-overlap, vector-near, Yarn graph via `via_graph=True`, or HippoRAG PPR via `query`+`via_graph=True`) | ~80/result |
| `hololoom_fetch` | Full payload by ID (use sparingly) | ~500–1k/each |
| `hololoom_timeline` | Para changelog window (Qdrant scroll over `swarm_materialized`, ts-sorted) | ~60/entry |
| `hololoom_interrogate` | From-outside Q&A over past session(s) — rung-2, routes `claude -p` | ~1 LLM call |
| `hololoom_provenance` | Git `Session:`-trailer attribution (who built this / is it holding up?) | ~40/commit |

All MCP tool calls are read-only. Writers live outside the tool surface — see
**Write-path rule** below.

### Write-path rule

The MCP server itself never mutates state. Writers split between two parties:

| Surface | Para writes | MCP indexers write |
|---|---|---|
| Qdrant | `swarm_materialized` | `claude_sessions`, `mythrl_docs`, `mythrl_git`, `mythrl_code` |
| Neo4j | `:ClaudeSession`/`Turn`/`Observation`, `:Shard`, `:Entity`, `:Concept` (HAS_TURN, FOLLOWS, MENTIONS, DERIVED_FROM_TURN, …) | `:Bobbin` meta-label + `:DocChunk`, `:Commit`, `:CodeSymbol`, `:File`, `:Repo` (IN_FILE, IN_REPO) |

Para's writers run as the bot swarm + enrichment-bot + materializer +
session-bobbin-materializer. MCP's writers are `tools/index_*.py` (Qdrant
collections) and `tools/yarn_writer.py` (Neo4j artifact graph), all under
launchd. The `claude_sessions` Qdrant collection is the spot where naming
might mislead: it's a filesystem mirror of `~/.claude/projects/*.jsonl`
written by MCP — same source as Para's session-bobbin-materializer reads
from Matrix-relayed events, but text-indexed independently. The two are
joined at query time via `turn_uuid` (see `_navigate_by_graph` in `server.py`).

### Search corpora

`hololoom_search` defaults to `corpus="all"` and merges by score. Restrict
when intent is clear:

| Corpus | Source | Indexer |
|---|---|---|
| `swarm` | `swarm_materialized` Qdrant collection (Matrix / voice memo derived) | Para enrichment bot |
| `sessions` | Claude Code transcripts under `~/.claude/projects/` | `tools/index_sessions.py` |
| `docs` | `*.md`, `*.rst`, `SESSION.json`, `context_cards.json` across configured repos | `tools/index_docs.py` |
| `git` | Commit subject+body across configured repos | `tools/index_git.py` |
| `code` | Python symbols (function/class/method) via stdlib `ast` | `tools/index_code.py` |

Configured repos live in `tools/repos.json`. Add a repo path → docs/git/code/grep all pick it up next run.

## Quickstart (P0 — orient only, no infra needed)

```bash
cd hololoom_mcp
uv venv && source .venv/bin/activate
uv pip install "mcp[cli]" pydantic
```

Open Claude Code in this directory:

```bash
claude
```

Claude Code reads `CLAUDE.md` and `.mcp.json` automatically. The session-start
protocol fires: `hololoom_orient` runs, `SESSION.json` is read, the agent
reports orientation in one line, then waits for input.

For P1+ (when wiring Yarn/Warp), add to your venv:

```bash
uv pip install neo4j qdrant-client sentence-transformers
```

## Two-layer state model

**Canon (durable):** `context_cards.json` — architecture, glossary, active
threads, recent decisions, infra inventory. Curate by hand for now; long
term, Para enrichment bot promotes durable decisions here.

**Volatile (per-session):** `SESSION.json` — what just happened, what's
still open, what's the next concrete step. Read at session start, updated
continuously, cleaned at session end via `/handoff`.

Run `/handoff` before exit. Schema in `.claude/skills/handoff/SKILL.md`.
Total budget under 1500 tokens.

## Slash commands

- `/orient` — bootstrap or re-orient mid-session. Optional topic argument:
  `/orient triton`, `/orient memory-bus`, etc.
- `/handoff` — write session-end state to `SESSION.json` before exit.

Both live as skills under `.claude/skills/` (Claude Code v2.1.101+ pattern;
custom commands merged into skills).

## Phase plan

- **P0 — `orient` only** ✅ shipped. No databases.
- **P1 — `search` + `fetch`** ✅ shipped against `swarm_materialized`.
  Embedder coordinated by routing through Para's `:8765` service (no env
  var alignment needed).
- **P2 — `navigate`** ✅ shipped. Default Qdrant-only (entity-overlap +
  vector-near). `via_graph=True` dispatches by seed type: yarn_writer's
  `:Bobbin` (docs/code/commits) traverses IN_FILE; sessions resolve via
  Qdrant payload `source_uuid` → materializer's `:ClaudeSessionTurn` and
  traverse FOLLOWS / HAS_TURN / DERIVED_FROM_TURN. HippoRAG v2 PPR
  (`navigator.py`) is live and **corpus-scoped to the experience tier**
  (2026-05-30): the synonym-graph gate is populated (~7.4k SYNONYM_OF edges),
  so `query`+`via_graph=True` runs PPR, but returns only experience-tier
  passages (ClaudeObservation / Shard / session) — the beekeeping/MirrorCore
  testbed sharing the graph is suppressed. Recall is thin by coverage: only
  186 `:ClaudeObservation` + 18 `:Shard` carry MENTIONS (raw session turns
  carry zero), and the 92× turn→observation condensation drops canon-central
  vocabulary. Remaining work (Para territory): richer concept extraction over
  turns — not just "add MENTIONS." See `project_hipporag_ppr_live_over_testbed`.
- **P3 — `timeline`** still scrolls `swarm_materialized` only. Cross-corpus
  ts-windowing against the `:Bobbin` artifact graph is now feasible
  (yarn_writer carries `mtime`/`date`); not yet wired.
- **P4 — auto-curate** `context_cards.json` from Para enrichment bot.
- **P5 — multi-corpus expansion** ✅ shipped: docs, git, code corpora +
  `hololoom_grep` literal-search escape hatch.
- **P6 — artifact graph in Neo4j** ✅ shipped. `tools/yarn_writer.py`
  projects docs/git/code Qdrant points into `:Bobbin` + `:File`/`:Repo`,
  enabling IN_FILE co-membership traversal. Sessions are deliberately not
  written here — Para's session-bobbin-materializer is canonical.

## Deployment options

**Local stdio (default).** Each developer runs the server. Already configured
in `.mcp.json`.

**mythrl-core HTTP/SSE.** One server, all devices via Tailscale. Switch the
entrypoint in `server.py`:

```python
mcp.run(transport="streamable-http", host="0.0.0.0", port=8765)
```

Then in `.mcp.json`:

```json
{
  "mcpServers": {
    "hololoom": { "url": "http://mythrl-core:8765/mcp" }
  }
}
```

## Token budget verification

```bash
python -c "
from server import hololoom_orient, OrientInput
out = hololoom_orient(OrientInput())
print(len(out)//4, 'tokens approx,', len(out), 'chars')
"
```

Practical floor: ~2800 tokens. Hard ceiling: 3500 tokens. The original 2000
ceiling is no longer realistic — `active_threads` alone now runs ~1000 tokens
when 3 active arcs are in motion (parallel sessions emit canon faster than
arcs land), and `architecture` + `glossary` together hold steady at ~1300
tokens given the current substrate breadth. Prior ceilings (1500 aspirational,
2000 hard) were written when substrate was smaller — both dead.

When the brief climbs above 3500: prune `active_threads` (drop landed work
at /handoff; orient already caps at 3 most-recent), tighten `summary` fields
in `context_cards.json`, age `recent_decisions` into `architecture`, or cut
`related_sessions` top_k (currently 1). The structural cost is `active_threads`
under parallel-session pressure; mechanical caps in `server.py` are the
last-resort knobs.

Cost composition, re-measured 2026-07-25 after a `context_cards.json` tightening
pass (prior figures were stale — `architecture` had drifted to ~1130 tok and
`recent_decisions` was never budgeted at all):
- architecture ~985 tok — durable; the floor rises as the stack grows
- glossary ~670 tok — durable, hard to compress further
- recent_decisions ~610 tok — was missing from this table entirely
- infra_inventory ~425 tok — fixed
- active_threads ~340–950 tok (cap=3) — fresh-arc-driven, varies with activity
- related_sessions ~105 tok (top_k=1) — continuity surface; absent in a fresh
  worktree with no overlapping session
- working_preferences + instructions + workplan_briefs ~245 tok — fixed

Measured total ~3270 tok in a worktree, ~3370 on `main` (where
`related_sessions` populates). Re-measure with the snippet above rather than
trusting these numbers — they drift as entries accumulate status parentheticals.

The drift mechanism to watch: `architecture` and `recent_decisions` summaries
accrete dated provenance (SHAs, ratification dates, per-clause dispositions)
that belongs in the pointed-to pin or doc. Orient's job is orientation; the
pointer is enough. Keep each summary to *what it is + current status + pointer*.

## Curating context_cards.json

The orient brief is only as good as this file. Update when:

- A new architectural decision lands → append to `recent_decisions`
- An active thread rotates (Triton ships, new thread opens) → swap
  `active_threads`
- A glossary term gets coined → add to `glossary`

Long term, this becomes Para enrichment bot's job (P4). For now, hand-curated.
