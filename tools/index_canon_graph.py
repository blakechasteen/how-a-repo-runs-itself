#!/usr/bin/env python3
"""
index_canon_graph.py — materialize the AUTHORED canon pin-graph into Neo4j.

The memory pins (~/.claude/projects/.../memory/*.md) already form a
hand-curated knowledge graph: bodies cross-reference each other with
[[wiki-links]] and frontmatter carries `tensions_with`. That is the artifact
tier's natural CITATION graph (per CLAUDE.md's two-tier rule — explicitly NOT
HippoRAG/PPR over a synonym graph; different data shape, right algorithm). v0
materializes it so canon becomes *traversable* — lineage, tensions, centrality —
which flat vector search structurally cannot do (similarity != connection).

MCP-owned, distinct label namespace (no collision with Para's experience graph
or yarn_writer's :Bobbin family):

  (:CanonPin {slug, title, pin_type, description, exists})
  (a:CanonPin)-[:CITES]->(b:CanonPin)          # from [[links]] in the body
  (a:CanonPin)-[:TENSIONS_WITH]->(b:CanonPin)  # from frontmatter tensions_with

`exists=false` marks a dangling target — a [[link]] to a pin not yet written
(the memory format treats those as "worth writing later", so they're real
signal, kept as property-less stubs).

Clean-rebuild each run (DETACH DELETE the :CanonPin projection, then rebuild
from source) so the graph always matches the current pins — no stale edges.
The projection is owned solely by this script, so the delete is safe.

One-shot / manual for now — NOT launchd-registered (greenlight-scope: an
always-on writer is a separate, explicit decision).

Run: PYTHONPATH=. ./.venv/bin/python tools/index_canon_graph.py [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx
from neo4j import GraphDatabase

def _main_checkout_root() -> Path:
    """Repo root of the PRIMARY checkout, even when run from a worktree.

    Worktrees live at <root>/.claude/worktrees/<name>/, so a worktree copy of
    this file resolves parents[2] to the worktree rather than the repo. The
    memory dir is a property of the repo — Claude keys its project scope on
    the main checkout's path — so normalize back to it.
    """
    root = Path(__file__).resolve().parents[2]
    marker = "/.claude/worktrees/"
    text = str(root)
    if marker in text:
        return Path(text.split(marker)[0])
    return root


# Claude's project-scope slug is the main checkout's path with "/" -> "-".
# Derived rather than hardcoded so the tool carries no operator username
# (Gate 5, 2026-07-25) and works on any checkout. Verified byte-identical to
# the literal it replaced.
MEMORY_DIR = Path(os.environ.get(
    "HOLOLOOM_MEMORY_DIR",
    str(Path.home() / ".claude" / "projects"
        / str(_main_checkout_root()).replace("/", "-") / "memory"),
))
NEO4J_URI = os.environ.get(
    "HOLOLOOM_NEO4J_URI",
    os.environ.get("NEO4J_URL", "bolt://127.0.0.1:7687"),
)
NEO4J_USER = os.environ.get(
    "HOLOLOOM_NEO4J_USER", os.environ.get("NEO4J_USER", "neo4j"),
)
NEO4J_PASSWORD = os.environ.get(
    "HOLOLOOM_NEO4J_PASSWORD", os.environ.get("NEO4J_PASSWORD", "CHANGE_ME"),
)
EMBED_URL = os.environ.get(
    "HOLOLOOM_EMBEDDING_SERVICE_URL", "http://127.0.0.1:8765",
)

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
FENCE = "---"
_PREFIXES = ("project_", "feedback_", "user_", "reference_")
# Words used to NAME the [[link]] syntax in prose (the pin documenting the
# graph mechanism trips its own extractor) — suppress them as fake targets.
_LINK_METALANGUAGE = {"link", "links", "wiki_link", "wiki_links",
                      "wikilink", "wikilinks"}


def _norm(raw: str) -> str:
    return raw.strip().lower().replace("-", "_").replace(" ", "_")


def resolve(raw: str, real: set[str],
            title_index: list[tuple[str, str]] | None = None) -> str | None:
    """Resolve a hand-authored [[link]] target to a canonical pin slug. Humans
    write inconsistent slugs — missing the project_/feedback_ prefix, hyphens
    for underscores, OR the concept name rather than the filename. Normalize,
    try the prefixes, then fall back to matching the concept against pin TITLES.
    Returns a real slug, a normalized dangling slug, or None for junk."""
    n = _norm(raw)
    if not re.fullmatch(r"[a-z0-9_]{3,}", n) or n in _LINK_METALANGUAGE:
        return None  # junk ('...', a fragment) or link-syntax metalanguage
    if n in real:
        return n
    for pre in _PREFIXES:
        if pre + n in real:
            return pre + n
    for pre in _PREFIXES:  # author double/mis-prefixed
        if n.startswith(pre) and n[len(pre):] in real:
            return n[len(pre):]
    # Concept->filename fallback: a [[link]] written as the concept name
    # (e.g. 'refuse_false_dichotomies') won't prefix-match the filename slug
    # (user_intellectual_integration_pattern) — match it against pin titles.
    if title_index is not None and len(n) >= 10:
        for slug, tnorm in title_index:
            if tnorm.startswith(n):
                return slug
    return n  # genuinely dangling (normalized form)


def _tw_target(raw: str) -> str:
    """One authored tensions_with item -> its slug token. Pins write these
    with trailing '# why' comments, '(annotation)' suffixes, and '.md'
    filename suffixes — strip all three; resolve() handles the rest."""
    item = raw.split("#", 1)[0].strip().strip("'\"")
    token = item.split()[0] if item.split() else ""
    return token[:-3] if token.endswith(".md") else token


def parse_pin(path: Path) -> dict:
    """Parse one pin into {slug, title, pin_type, description, links,
    tensions_with}. Dependency-free flat frontmatter (no PyYAML), matching
    tools/index_docs.parse_frontmatter; only the fields this graph needs."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    slug = path.stem
    fm: dict[str, str] = {}
    fm_lines: list[str] = []
    body = text
    if text.startswith(FENCE):
        lines = text.splitlines()
        end = next((i for i in range(1, len(lines))
                    if lines[i].strip() == FENCE), None)
        if end is not None:
            fm_lines = lines[1:end]
            for line in fm_lines:
                if not line or line[0] in (" ", "\t", "-", "#") or ":" not in line:
                    continue
                k, _, v = line.partition(":")
                fm[k.strip().lower()] = v.strip()
            body = "\n".join(lines[end + 1:])

    # Body [[wiki-links]] (dedup, drop self-reference).
    links: list[str] = []
    for tgt in WIKILINK_RE.findall(body):
        t = tgt.strip()
        if t and t != slug and t not in links:
            links.append(t)

    # tensions_with: inline `[a, b]` OR YAML block list. The flat key:value
    # loop above skips indented/dash lines, so block-form items (the form 3
    # of the 4 authored pins actually use) are recovered from the raw
    # frontmatter lines here — inline-only parsing silently dropped 13
    # authored tension edges (2026-06-09 corpus census).
    raw_tw = fm.get("tensions_with", "").strip()
    if raw_tw.startswith("[") and raw_tw.endswith("]"):
        items = raw_tw[1:-1].split(",")
    else:
        items, in_tw = [], False
        for line in fm_lines:
            k, has_colon, _ = line.partition(":")
            s = line.strip()
            if has_colon and k.strip().lower() == "tensions_with":
                in_tw = True
            elif in_tw and s.startswith("- "):
                items.append(s[2:])
            elif in_tw and has_colon and not s.startswith("-"):
                break  # next frontmatter key ends the block
    tw: list[str] = []
    for x in items:
        t = _tw_target(x)
        if t and t not in tw:
            tw.append(t)

    return {
        "slug": slug,
        "title": fm.get("name") or slug,
        "pin_type": fm.get("type", ""),
        "description": fm.get("description", ""),
        "links": links,
        "tensions_with": tw,
        "body": body,
    }


# ---------------------------------------------------------------------------
# Prose-citation extraction (canon_graph_prose_edges slice, 2026-06-07).
#
# v0 captured only [[wiki-link]] edges. A probe (tools/probe_prose_edges.py)
# showed 47% of pins (55/116) reference other canon in PROSE, not [[]] — 347
# missing edges, concentrated on the foundational pins (autonomy_thesis,
# north_star), so [[]]-only centrality under-ranks exactly the load-bearing
# canon. Two passes recover them as DISTINCT, source-tagged trust tiers
# (never blurred into authored [[]] :CITES — project_interpretation_tier):
#   - prose (symbolic): a real slug appears as a token in the body outside [[]].
#     Blake WROTE the slug, so it's :CITES {source:'prose'} (authored family,
#     distinct bucket). High-precision, no LLM.
#   - llm (conceptual): the pin invokes another BY IDEA with no slug token.
#     LLM-inferred structure over authored content → :INVOKES {source:'llm'}
#     (a separate relationship so it can never be read as authored).
# ---------------------------------------------------------------------------

_TOKEN_L, _TOKEN_R = r"(?<![a-z0-9_])", r"(?![a-z0-9_])"


def _slug_forms(real: set[str]) -> dict[str, str]:
    """Map prose surface-forms -> canonical slug. A pin is referenced in prose by
    its full slug (project_foo_bar) or prefix-stripped slug (foo_bar) — both
    slug-shaped, so word-boundary matching is high-precision. Forms < 8 chars
    are dropped (short stems collide with ordinary prose).

    Full slugs are unique (always kept). A prefix-stripped STEM is kept only when
    UNAMBIGUOUS — exactly one pin yields it and it isn't itself another pin's full
    slug. Otherwise a bare mention of that stem can't be confidently attributed,
    so the form is dropped rather than guessed (deterministic; 0 collisions in the
    current corpus, but this hardens against a future cross-prefix clash)."""
    from collections import defaultdict
    forms: dict[str, str] = {slug: slug for slug in real}  # full slugs: unambiguous
    stem2slugs: dict[str, set[str]] = defaultdict(set)
    for slug in sorted(real):
        for pre in _PREFIXES:
            if slug.startswith(pre) and len(slug[len(pre):]) >= 8:
                stem2slugs[slug[len(pre):]].add(slug)
    for stem, slugs in stem2slugs.items():
        if len(slugs) == 1 and stem not in forms:  # unambiguous + not a full slug
            forms[stem] = next(iter(slugs))
    return forms


def extract_prose_links(pins: list[dict], real: set[str]) -> None:
    """SYMBOLIC pass: sets p['prose_links'] — real slugs appearing as tokens in
    the body OUTSIDE [[ ]] that aren't already an authored [[]] edge. Run AFTER
    the resolve pass (p['links'] canonical). High-precision (probe-verified:
    347 edges, spot-checked 0 phantom — slug-shaped prose tokens are deliberate
    references)."""
    compiled = [
        (re.compile(_TOKEN_L + re.escape(f) + _TOKEN_R), s)
        for f, s in _slug_forms(real).items()
    ]
    for p in pins:
        body = WIKILINK_RE.sub(" ", p["body"]).lower()
        authored = set(p["links"])
        p["prose_links"] = sorted(
            {tgt for rx, tgt in compiled
             if tgt != p["slug"] and tgt not in authored and rx.search(body)}
        )


_LLM_PROMPT = """You are extracting a CITATION graph over a set of memory "pins" (canon notes).

TARGET PIN: {slug}
TITLE: {title}
BODY:
\"\"\"
{body}
\"\"\"

CATALOG — every pin you may reference (slug: title), one per line:
{catalog}

TASK: Return the slugs of OTHER pins the TARGET PIN substantively INVOKES in its
prose — it builds on, depends on, resolves, extends, or directly discusses that
pin's idea. Only references a careful reader would mark as "this note is talking
about that note."

STRICT RULES:
- Choose ONLY slugs that appear verbatim in the CATALOG. Never invent one.
- Do NOT include the target pin itself.
- Be conservative: omit if unsure. Vague topical overlap is NOT a citation.
- Output ONLY a JSON array of slug strings (e.g. ["project_foo","feedback_bar"]).
  No prose, no markdown fence. Empty array [] if none.
"""


def _claude_p(prompt: str, model: str, timeout: float = 120.0,
              retries: int = 1) -> str | None:
    """One headless Claude call via the `claude -p` CLI — Max OAuth, no API key
    (feedback_max_over_api_for_cron). MCP-disabled + neutral cwd so it doesn't
    load this repo's own MCP server. Retries once on failure.

    Returns the stdout string on success (which may legitimately be '[]'), or
    None on HARD failure (nonzero exit / timeout / empty stdout). None is kept
    DISTINCT from '[]' so callers don't silently count a failed call as a
    model 'reject all' — feedback_no_fabricated_results."""
    import subprocess
    for _ in range(retries + 1):
        try:
            r = subprocess.run(
                ["claude", "-p", "--strict-mcp-config", "--model", model, prompt],
                capture_output=True, text=True, timeout=timeout, cwd="/tmp",
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except Exception:
            pass
    return None


def _parse_slug_list(out: str | None, real: set[str]) -> set[str]:
    """Pull a JSON slug array from model output; keep ONLY real slugs (grounding
    enforcement — invented targets dropped even if the model emits them). A None
    `out` (hard call failure) yields the empty set — callers must check for None
    separately to distinguish failure from a genuine empty result."""
    if not out:
        return set()
    import json as _json
    m = re.search(r"\[.*\]", out, re.DOTALL)
    if not m:
        return set()
    try:
        arr = _json.loads(m.group(0))
    except Exception:
        return set()
    return {s for s in arr if isinstance(s, str) and s in real}


_LLM_VERIFY_PROMPT = """You AUDIT a citation graph — adversarially. A weaker model proposed that the
SOURCE pin invokes each CANDIDATE below. Most proposals are wrong (topical
overlap, shared vocabulary), so be skeptical: confirm a candidate ONLY if the
SOURCE pin's prose SUBSTANTIVELY invokes that candidate's specific idea — builds
on it, depends on it, resolves/extends/directly discusses it. Sharing a theme or
a word is NOT enough. When unsure, REJECT.

SOURCE pin: {slug}
SOURCE body:
\"\"\"
{body}
\"\"\"

CANDIDATES (slug: what it's about):
{candidates}

Output ONLY a JSON array of the slugs you CONFIRM (a subset of the candidate
slugs). [] if none survive. No prose."""


def extract_llm_links(pins: list[dict], real: set[str], model: str,
                      verify_model: str | None = None,
                      max_workers: int = 6) -> tuple[int, int]:
    """LLM CONCEPTUAL pass with a PROPOSE→VERIFY gate (builder_cannot_self_verify
    baked into the pipeline): sets p['llm_links'] — pins invoked BY IDEA (no slug
    token), which the symbolic passes can't catch.

      propose  `model` (recall-liberal) emits candidates, grounded to the real-
               slug CATALOG, minus refs already caught as [[]]/prose.
      verify   a DISTINCT, skeptical `verify_model` confirms each candidate
               against the source prose; only confirmed edges survive. (A 12-edge
               opus audit of the un-gated sonnet pass confirmed just 6/12 — the
               gate is why the :INVOKES tier is trustworthy, not the extractor.)

    With verify_model=None the gate is skipped (raw proposals kept — for probing
    only). Returns (proposed, kept, fails) where fails counts hard call failures
    so a flaky `claude -p` can't masquerade as the gate rejecting edges
    (feedback_no_fabricated_results)."""
    from concurrent.futures import ThreadPoolExecutor
    catalog = "\n".join(f"{p['slug']}: {p['title']}" for p in pins)
    about = {p["slug"]: f"{p['title']}. {p['description']}"[:240] for p in pins}
    fails = {"propose": 0, "verify": 0, "verify_cands_dropped": 0}

    def propose(p: dict) -> None:
        already = set(p["links"]) | set(p.get("prose_links", [])) | {p["slug"]}
        out = _claude_p(
            _LLM_PROMPT.format(slug=p["slug"], title=p["title"],
                               body=p["body"][:6000], catalog=catalog), model)
        if out is None:
            fails["propose"] += 1
        p["_llm_proposed"] = sorted(_parse_slug_list(out, real) - already)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        list(ex.map(propose, pins))
    proposed = sum(len(p["_llm_proposed"]) for p in pins)

    if not verify_model:
        for p in pins:
            p["llm_links"] = p["_llm_proposed"]
        return proposed, proposed, fails

    def verify(p: dict) -> None:
        cands = p["_llm_proposed"]
        if not cands:
            p["llm_links"] = []
            return
        cand_block = "\n".join(f"{c}: {about.get(c, c)}" for c in cands)
        out = _claude_p(
            _LLM_VERIFY_PROMPT.format(slug=p["slug"], body=p["body"][:5000],
                                      candidates=cand_block), verify_model)
        if out is None:  # verify call FAILED — fail-closed (drop) but COUNT it,
            fails["verify"] += 1           # don't silently bank it as a rejection
            fails["verify_cands_dropped"] += len(cands)
            p["llm_links"] = []
            return
        # Confirmed set is constrained to the proposed candidates (can't add new).
        p["llm_links"] = sorted(_parse_slug_list(out, set(cands)))

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        list(ex.map(verify, [p for p in pins if p["_llm_proposed"]]))
    for p in pins:
        p.setdefault("llm_links", [])
    kept = sum(len(p["llm_links"]) for p in pins)
    return proposed, kept, fails


def _embed(texts: list[str]) -> list[list[float]]:
    """Embed via the shared :8765 service, normalized (so dot == cosine)."""
    out: list[list[float]] = []
    for i in range(0, len(texts), 32):
        r = httpx.post(
            f"{EMBED_URL}/embed",
            json={"text": [t[:1500] for t in texts[i:i + 32]], "normalize": True},
            timeout=60.0,
        )
        r.raise_for_status()
        out.extend(r.json()["vectors"])
    return out


def add_similarity_edges(driver, pins: list[dict], k: int, threshold: float) -> int:
    """DERIVED densification (per the canon_graph_densify brief): add weighted
    :SIMILAR_TO edges between semantically-near pins via embedding kNN. Kept
    LABEL-DISTINCT from authored :CITES per [[project_interpretation_tier]] —
    these are *computed*, not authored, and must never read as ground truth.
    Bounded by k + threshold; clean-rebuild (delete :SIMILAR_TO, recompute)."""
    vecs = _embed([f"{p['title']}. {p['description']}" for p in pins])
    slugs = [p["slug"] for p in pins]
    n = len(slugs)
    edges: list[tuple[str, str, float]] = []
    for i in range(n):
        ranked = sorted(
            ((sum(a * b for a, b in zip(vecs[i], vecs[j])), j)
             for j in range(n) if j != i),
            reverse=True,
        )
        for cos, j in ranked[:k]:
            if cos >= threshold:
                edges.append((slugs[i], slugs[j], round(float(cos), 4)))
    with driver.session() as s:
        s.run("MATCH ()-[r:SIMILAR_TO]->() DELETE r")
        for a, b, cos in edges:
            s.run(
                "MATCH (x:CanonPin {slug:$a}), (y:CanonPin {slug:$b}) "
                "MERGE (x)-[r:SIMILAR_TO]->(y) SET r.cos=$cos",
                a=a, b=b, cos=cos,
            )
    return len(edges)


def compute_centrality(pins: list[dict]) -> tuple[dict, dict, dict]:
    """Precompute graph metrics over the AUTHORED citation graph so the read tool
    (hololoom_canon) stays pure fast Cypher — no networkx at query time (per the
    canon_graph_query_tool brief, fork 2). Authored = [[]] (source:'wikilink') +
    prose (source:'prose') — both are Blake-WRITTEN references, so both belong in
    the citation centrality. (Excludes :INVOKES llm edges — those are inferred,
    not authored, and must not inflate authored centrality.) Metrics are DERIVED
    FROM authored edges but not themselves authored:
      - indegree     citation in-degree (how load-bearing)
      - betweenness  bridge-ness (fraction of shortest authored paths through it)
      - community_id topic cluster (undirected greedy-modularity partition)
    Recovering prose edges here is the whole point of the slice: it un-distorts
    centrality, which [[]]-only systematically under-ranked on foundational pins
    (autonomy_thesis, north_star). ~120 nodes makes this instant; no self-loops
    (parse_pin + resolve drop self-reference), so betweenness is well-defined."""
    import networkx as nx  # lazy: only the materializer needs it, never server.py

    g = nx.DiGraph()
    for p in pins:
        g.add_node(p["slug"])
    for p in pins:
        for t in p["links"] + p.get("prose_links", []):  # authored = wikilink+prose
            g.add_edge(p["slug"], t)  # auto-adds dangling targets as nodes
    indeg = dict(g.in_degree())
    btw = nx.betweenness_centrality(g)
    comm: dict[str, int] = {}
    for cid, members in enumerate(
        nx.community.greedy_modularity_communities(g.to_undirected())
    ):
        for node in members:
            comm[node] = cid
    return indeg, btw, comm


def stamp_metrics(s, indeg: dict, btw: dict, comm: dict,
                  indeg_wiki: dict | None = None,
                  indeg_prose: dict | None = None,
                  indeg_llm: dict | None = None) -> None:
    """Write precomputed centrality onto each :CanonPin (idempotent SET).
    `indegree` is the AUTHORED total (wikilink+prose); the per-source breakdown
    (indegree_wikilink / _prose / _llm) lets the read tool show the corrected
    centrality with its provenance split."""
    iw, ip, il = indeg_wiki or {}, indeg_prose or {}, indeg_llm or {}
    for slug in set(indeg) | set(btw) | set(comm) | set(iw) | set(ip) | set(il):
        s.run(
            "MATCH (c:CanonPin {slug:$slug}) "
            "SET c.indegree=$i, c.betweenness=$b, c.community_id=$cid, "
            "    c.indegree_wikilink=$iw, c.indegree_prose=$ip, c.indegree_llm=$il",
            slug=slug,
            i=int(indeg.get(slug, 0)),
            b=round(float(btw.get(slug, 0.0)), 6),
            cid=int(comm.get(slug, -1)),
            iw=int(iw.get(slug, 0)),
            ip=int(ip.get(slug, 0)),
            il=int(il.get(slug, 0)),
        )


def write_meta(s, built_at: str) -> dict:
    """Stamp the singleton :CanonGraphMeta freshness node from LIVE counts (so
    it's truthful even after a no-`--similar` rebuild wiped SIMILAR_TO). The
    read tool reads `built_at` and compares it to pin mtimes to flag staleness —
    the graph is materialized by a MANUAL one-shot run, so freshness must be
    visible, not assumed (canon_graph_query_tool brief, 'freshness honesty').
    NOT a :CanonPin, so the projection's DETACH DELETE never touches it."""
    one = lambda q: s.run(q).single()["n"]
    counts = {
        "pins": one("MATCH (c:CanonPin) RETURN count(c) AS n"),
        "real": one("MATCH (c:CanonPin {exists:true}) RETURN count(c) AS n"),
        "stubs": one("MATCH (c:CanonPin {exists:false}) RETURN count(c) AS n"),
        "cites": one("MATCH ()-[r:CITES]->() RETURN count(r) AS n"),
        "cites_wikilink": one(
            "MATCH ()-[r:CITES {source:'wikilink'}]->() RETURN count(r) AS n"),
        "cites_prose": one(
            "MATCH ()-[r:CITES {source:'prose'}]->() RETURN count(r) AS n"),
        "invokes": one("MATCH ()-[r:INVOKES]->() RETURN count(r) AS n"),
        "tensions": one("MATCH ()-[r:TENSIONS_WITH]->() RETURN count(r) AS n"),
        "similar": one("MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) AS n"),
    }
    s.run(
        "MERGE (m:CanonGraphMeta {id:'singleton'}) "
        "SET m.built_at=$ts, m.pins=$pins, m.real=$real, m.stubs=$stubs, "
        "    m.cites=$cites, m.cites_wikilink=$cites_wikilink, "
        "    m.cites_prose=$cites_prose, m.invokes=$invokes, "
        "    m.tensions=$tensions, m.similar=$similar",
        ts=built_at,
        **counts,
    )
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="parse + report, no Neo4j writes")
    ap.add_argument("--similar", action="store_true",
                    help="also add derived :SIMILAR_TO edges (pin-embedding kNN)")
    ap.add_argument("--sim-k", type=int, default=5)
    ap.add_argument("--sim-threshold", type=float, default=0.66)
    ap.add_argument("--llm", action="store_true",
                    help="also add LLM-inferred conceptual :INVOKES edges "
                         "(grounded propose→verify `claude -p` pass; ~4 min)")
    ap.add_argument("--llm-model", default="sonnet",
                    help="PROPOSER model for the --llm pass (recall-liberal)")
    ap.add_argument("--llm-verify-model", default="opus",
                    help="VERIFIER model (distinct + skeptical) that gates each "
                         "proposed edge; builder_cannot_self_verify. '' to skip.")
    args = ap.parse_args()

    pins = [parse_pin(p) for p in sorted(MEMORY_DIR.glob("*.md"))
            if p.name != "MEMORY.md"]
    real = {p["slug"] for p in pins}
    title_index = [(p["slug"], _norm(p["title"])) for p in pins]

    # Resolve hand-authored [[link]] slugs to canonical pins before edges.
    for p in pins:
        seen: set[str] = set()
        out: list[str] = []
        for t in p["links"]:
            r = resolve(t, real, title_index)
            if r and r != p["slug"] and r not in seen:
                seen.add(r)
                out.append(r)
        p["links"] = out
        p["tensions_with"] = [
            r for r in (resolve(t, real, title_index) for t in p["tensions_with"])
            if r and r != p["slug"]
        ]

    # Symbolic prose-citation pass (always on — cheap, high-precision). Adds
    # p['prose_links']: real slugs mentioned in prose but not [[]]-linked.
    extract_prose_links(pins, real)

    n_cites = sum(len(p["links"]) for p in pins)
    n_prose = sum(len(p["prose_links"]) for p in pins)
    n_tw = sum(len(p["tensions_with"]) for p in pins)
    dangling = {t for p in pins for t in p["links"] if t not in real}
    print(f"[parse] {len(pins)} pins · {n_cites} wikilink-cites · "
          f"{n_prose} prose-cites · {n_tw} tensions · "
          f"{len(dangling)} truly-dangling targets")

    if args.dry_run:
        indeg = Counter(t for p in pins for t in p["links"] + p["prose_links"])
        print("[dry-run] top-cited (authored = wikilink+prose):",
              ", ".join(f"{s}({n})" for s, n in indeg.most_common(6)))
        return 0

    # LLM conceptual pass (opt-in — slow). Propose→verify gate. Adds p['llm_links'].
    if args.llm:
        vm = args.llm_verify_model or None
        print(f"[llm] propose via `claude -p --model {args.llm_model}` → verify "
              f"via {vm or 'NONE (ungated)'} over {len(pins)} pins …")
        proposed, kept, fails = extract_llm_links(pins, real, args.llm_model,
                                                  verify_model=vm)
        rejected = proposed - kept - fails["verify_cands_dropped"]
        rate = f"{100*kept//proposed}%" if proposed else "n/a"
        print(f"[llm] {proposed} proposed → {kept} kept ({rate}) = +{kept} :INVOKES. "
              f"gate rejected {rejected}; call-failures: propose={fails['propose']} pins, "
              f"verify={fails['verify']} pins ({fails['verify_cands_dropped']} cands "
              f"fail-closed dropped)")

    indeg, btw, comm = compute_centrality(pins)
    built_at = datetime.now(timezone.utc).isoformat()

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as s:
        # Footgun guard: a clean rebuild DETACH-DELETEs every :CanonPin and so
        # wipes the LLM :INVOKES tier. Without --llm it is NOT rebuilt, silently
        # losing it — warn loudly so a routine symbolic refresh doesn't drop it.
        if not args.llm:
            inv = s.run("MATCH ()-[r:INVOKES]->() RETURN count(r) AS n").single()["n"]
            if inv:
                print(f"[warn] rebuild WITHOUT --llm will WIPE {inv} existing "
                      f":INVOKES edges — re-run with --llm to keep the extracted tier")
        # Clean rebuild of the projection (owned solely by this script).
        s.run("MATCH (c:CanonPin) DETACH DELETE c")
        for p in pins:
            s.run(
                "MERGE (c:CanonPin {slug:$slug}) "
                "SET c.title=$title, c.pin_type=$pin_type, "
                "    c.description=$description, c.exists=true",
                slug=p["slug"], title=p["title"],
                pin_type=p["pin_type"], description=p["description"],
            )
        for p in pins:
            # Authored [[]] links — source-tagged 'wikilink'.
            for t in p["links"]:
                s.run(
                    "MERGE (b:CanonPin {slug:$t}) ON CREATE SET b.exists=false "
                    "WITH b MATCH (a:CanonPin {slug:$slug}) "
                    "MERGE (a)-[r:CITES]->(b) SET r.source='wikilink'",
                    t=t, slug=p["slug"],
                )
            # Symbolic prose-cites — same :CITES family (Blake wrote the slug),
            # DISTINCT source so the read tool never blurs it into a [[]] link.
            for t in p["prose_links"]:
                s.run(
                    "MERGE (b:CanonPin {slug:$t}) ON CREATE SET b.exists=false "
                    "WITH b MATCH (a:CanonPin {slug:$slug}) "
                    "MERGE (a)-[r:CITES]->(b) SET r.source='prose'",
                    t=t, slug=p["slug"],
                )
            # LLM-inferred conceptual refs — SEPARATE relationship so they can
            # never read as authored (interpretation_tier: inferred structure).
            # propose→verify provenance: proposed by `model`, gated by `verified_by`.
            for t in p.get("llm_links", []):
                s.run(
                    "MERGE (b:CanonPin {slug:$t}) ON CREATE SET b.exists=false "
                    "WITH b MATCH (a:CanonPin {slug:$slug}) "
                    "MERGE (a)-[r:INVOKES]->(b) "
                    "SET r.source='llm', r.model=$model, r.verified_by=$vby",
                    t=t, slug=p["slug"], model=args.llm_model,
                    vby=(args.llm_verify_model or "ungated"),
                )
            for t in p["tensions_with"]:
                s.run(
                    "MERGE (b:CanonPin {slug:$t}) ON CREATE SET b.exists=false "
                    "WITH b MATCH (a:CanonPin {slug:$slug}) "
                    "MERGE (a)-[:TENSIONS_WITH]->(b)",
                    t=t, slug=p["slug"],
                )
        nodes = s.run("MATCH (c:CanonPin) RETURN count(c) AS n").single()["n"]
        stubs = s.run(
            "MATCH (c:CanonPin) WHERE c.exists=false RETURN count(c) AS n"
        ).single()["n"]
        cites_w = s.run("MATCH ()-[r:CITES {source:'wikilink'}]->() "
                        "RETURN count(r) AS n").single()["n"]
        cites_p = s.run("MATCH ()-[r:CITES {source:'prose'}]->() "
                        "RETURN count(r) AS n").single()["n"]
        invokes = s.run("MATCH ()-[r:INVOKES]->() RETURN count(r) AS n").single()["n"]
        tens = s.run(
            "MATCH ()-[r:TENSIONS_WITH]->() RETURN count(r) AS n"
        ).single()["n"]
        # Precomputed centrality (authored = wikilink+prose) + per-source in-degree.
        stamp_metrics(
            s, indeg, btw, comm,
            indeg_wiki=Counter(t for p in pins for t in p["links"]),
            indeg_prose=Counter(t for p in pins for t in p["prose_links"]),
            indeg_llm=Counter(t for p in pins for t in p.get("llm_links", [])),
        )
    print(f"[done] :CanonPin={nodes} ({len(real)} real, {stubs} dangling stubs) "
          f"· :CITES wikilink={cites_w} prose={cites_p} · :INVOKES={invokes} "
          f"· :TENSIONS_WITH={tens} · centrality stamped (authored=wikilink+prose)")

    if args.similar:
        n_sim = add_similarity_edges(driver, pins, args.sim_k, args.sim_threshold)
        print(f"[similar] +{n_sim} derived :SIMILAR_TO edges (k={args.sim_k}, "
              f"threshold={args.sim_threshold}) — label-distinct from authored :CITES")

    # Freshness node LAST, from live counts (so :SIMILAR_TO is reflected).
    with driver.session() as s:
        meta = write_meta(s, built_at)
    print(f"[meta] :CanonGraphMeta built_at={built_at} · {meta}")
    driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
