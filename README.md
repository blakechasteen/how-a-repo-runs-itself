# How a repo runs itself

A curated, publicly-emitted subset of the operating system of a real
human–AI working corpus — the protocols by which fresh AI sessions orient
in one tool call, parallel sessions coexist without clobbering each other,
and an AI-co-authored knowledge base keeps from collapsing into its own echo.

**Start here → [`docs/how_this_repo_runs_itself.md`](docs/how_this_repo_runs_itself.md)** — the method essay. Everything else is the machinery it describes.

## What's in here

This is a *subset*, chosen by an allowlist (deny-by-default), not a scrub of
a full corpus. 51 files:

| Path | What |
|---|---|
| `docs/how_this_repo_runs_itself.md` | the method essay (read first) |
| `CLAUDE.md`, `CLAUDE_HISTORY.md` | the operating contract + its history — the rules every session follows |
| `hololoom_mcp_README.md` | the read-surface server this all runs over |
| `conventions/` | the four `_CONVENTION` docs: workplan briefs, kickoff prompts, reading-lenses, the peer inbox |
| `docs/` | worked examples (the MAST collision-class self-audit), an FAQ, three external-research surveys, LBP protocol specs |
| `tools/` | eleven of the actual mechanisms — brief sweep, cross-session coordination, the governance diff-gate, session digests, the canon citation-graph indexer, and the disposition signer (+ its tests) |
| `pins/` | 24 method-discipline memory pins — the load-bearing lessons, each earned by at least one incident |

## What this is *not*

- **Not the whole corpus.** Voice memos, raw session transcripts, business
  strategy, and anything touching third parties or AI peers without their
  consent were excluded *by selection*, not redaction.
- **Not a runnable product.** These are artifacts showing *how the method
  works*. Some tools carry as-is localhost defaults and paths; a public
  default credential was genericized to `CHANGE_ME`.
- **Not a one-way mirror of a live system's secrets.** Every file passed a
  five-gate audit (secrets scan, third-party-name scan, provenance check,
  a per-file human read, and a topology/service-disclosure scan) before it
  shipped — **with one recorded exception.** The two signing tools added
  2026-08-04 (`tools/disposition_sign.py`, `tools/test_disposition_sign.py`,
  and the signing extension to `tools/brief_disposition.py`) cleared the four
  mechanical gates, and their three disclosure questions were each ruled on
  individually — but the per-file human read was **deliberately waived**, not
  performed. It is named here rather than smoothed over, because a gate you
  skipped and a gate you passed are different facts. See
  [`PROVENANCE.md`](PROVENANCE.md).

## Provenance & how this was emitted

This subset was produced by the corpus's own emission discipline: "the
public" is treated as a *party*, and substrate crosses a party boundary only
by an explicit, enumerated, human-ratified contract — never by bulk copy.
The full story, including the gate that caught a hardcoded credential the
mechanical secret-scanner missed, is in [`PROVENANCE.md`](PROVENANCE.md).

## License

- **`tools/`** — Apache-2.0 (see [`LICENSE`](LICENSE))
- **Everything else** (docs, pins, conventions, `CLAUDE.md`) —
  Creative Commons Attribution 4.0 (see [`LICENSE-docs`](LICENSE-docs))

Attribution: Blake Chasteen. Portions synthesized in collaboration with
Claude (Anthropic); AI-interpreted memory pins carry an `interpreted_by`
marker in their frontmatter.
