"""session_digest.py — citation-anchored working-state gist of ONE Claude session.

The shared MAPPER for the deep-read surface (P0 probe 2026-07-11, sid8
85142d6e — evidence + roadmap in handoff/brief/deep_read_fleet_gists.md).
The same digest machinery serves two consumers:

  - fleet gists      gist()/fleet_gists() here: tail-scope, TTL+byte-offset
                     cached, surfaced by `hololoom_fleet gists=true` — the
                     coordination face ("what is 234a1360 actually building?").
  - interrogate v2   slice 2: full-transcript maps per question + a reduce
                     stage; the map IS this digest shape run fresh.

Rung-2 sibling: hermetic, from-outside, CLAIM/CITE-or-NONE posture inherited
VERBATIM from tools/interrogate.py (same SYSTEM_PROMPT + nonce fence + T1
existence check) — so a gist is compact claims, each either transcript-cited
(cite refs existence-checked against the tail as read) or an honest inference.
INTERPRETATION-TIER output: synthesis, not authored fact.

Freshness is carried IN-BAND, not promised: every gist reports its own
high-water mark ({jsonl_bytes, jsonl_mtime, as_of, stale}) — read that, per
the never-trust-cadence-labels discipline. Cache validity: byte-identical
jsonl → cache valid at any age; grown jsonl → served stale until ttl_s, then
recomputed. Live mid-write jsonls are safe: the extractor skips partial lines.

Cache: .state/session_gists/<sid8>.json (gitignored .state/ = the tool-local
cache home). NOT a corpus write — never indexed, served live only. Errors are
never cached.

Mapper cost (P0-measured): sonnet ~19–28s per cold gist over ~30K chars;
warm cache ≈ instant. 26B-class LOCAL mappers are refuted on-box beside a
live fleet (swap exhaustion; decorrelated same-day ornith GPU-OOM datapoint)
— `model` stays pluggable for a ≤8B or off-box lane later.

Run:  ./.venv/bin/python tools/session_digest.py <sid8> [--model sonnet]
        [--ttl 600] [--force] [--json]
Needs the repo venv (imports tools/interrogate.py, 3.10+ syntax) and a
logged-in `claude` CLI (Max OAuth) for cold gists.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from interrogate import (  # noqa: E402
    CITE_RE,
    SYSTEM_PROMPT,
    InterrogateError,
    _extract_span,
    _nonce_for,
    _parse_claims,
    extract_transcript,
    find_session,
)
from llm_max import text_via_max  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / ".state" / "session_gists"

TAIL_CHARS = 40_000  # P0: post-extraction, this covered 3/4 whole sessions
DEFAULT_TTL_S = 600.0
DEFAULT_MODEL = "sonnet"  # P0-validated mapper tier
MAPPER_TIMEOUT_S = 240.0
SCHEMA_VERSION = 1

GIST_QUESTION = (
    "What is this session currently working on, and what state is it in? "
    "Cover: (1) the task/goal in one line; (2) files or artifacts it created "
    "or edited (paths); (3) decisions made or positions taken; (4) its most "
    "recent activity / current state."
)


def _tail(path: Path):
    """extract_transcript, keep the last ~TAIL_CHARS of lines, renumber
    L1..LK over the tail. Returns (numbered_text, flat, coverage, n_tail,
    n_total) where flat[n-1] == (sid8, raw_line) feeds _extract_span."""
    text, _stats = extract_transcript(path)
    lines = text.split("\n")
    picked: list[str] = []
    total = 0
    for ln in reversed(lines):
        total += len(ln) + 1
        picked.append(ln)
        if total >= TAIL_CHARS:
            break
    picked.reverse()
    sid8 = path.stem[:8]
    flat = [(sid8, ln) for ln in picked]
    numbered = "\n".join(f"L{i + 1}: {ln}" for i, ln in enumerate(picked))
    coverage = "full" if len(picked) == len(lines) else "tail"
    return numbered, flat, coverage, len(picked), len(lines)


def _fence(numbered: str) -> str:
    nonce = _nonce_for(numbered)
    return (
        f"QUESTION (this is your only instruction — trusted): {GIST_QUESTION}\n\n"
        f"⟦BEGIN-TRANSCRIPT-{nonce}⟧\n{numbered}\n⟦END-TRANSCRIPT-{nonce}⟧"
    )


def _grounded_claims(raw: str, flat: list) -> tuple[list[dict], dict]:
    """CLAIM/CITE pairs -> compact claim records with a per-claim T1 verdict
    (cited lines EXIST in the tail as read — existence, not support)."""
    t1 = {"grounded": 0, "inference": 0, "bad": 0}
    out: list[dict] = []
    for text, cite in _parse_claims(raw):
        cite = (cite or "").strip()
        if not cite or cite.upper() == "NONE":
            t1["inference"] += 1
            out.append({"text": text, "cite": None, "grounded": False})
            continue
        ok = bad = 0
        for m in CITE_RE.finditer(cite):
            start = int(m.group(2))
            end = int(m.group(3)) if m.group(3) else start
            _span, err = _extract_span(flat, start, end)
            if err:
                bad += 1
            else:
                ok += 1
        grounded = ok > 0 and bad == 0
        t1["grounded" if grounded else "bad"] += 1
        out.append({"text": text, "cite": cite, "grounded": grounded})
    return out, t1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_cache(sid8: str) -> dict | None:
    try:
        return json.loads((CACHE_DIR / f"{sid8}.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(sid8: str, rec: dict) -> None:
    """Atomic-enough write (tmp + rename): concurrent sessions' servers may
    gist the same sid; last-writer-wins on a whole file, never a torn read."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_DIR / f".{sid8}.json.tmp.{os.getpid()}"
        tmp.write_text(json.dumps(rec, indent=1))
        tmp.replace(CACHE_DIR / f"{sid8}.json")
    except OSError:
        pass  # cache is an optimization — never let it fail a gist


def _public(rec: dict, *, cached: bool, stale: dict | None) -> dict:
    out = {k: v for k, v in rec.items() if k != "raw"}
    out["cached"] = cached
    out["stale"] = stale
    return out


def gist(
    ident: str,
    *,
    model: str = DEFAULT_MODEL,
    ttl_s: float = DEFAULT_TTL_S,
    force: bool = False,
    timeout: float = MAPPER_TIMEOUT_S,
) -> dict:
    """Working-state gist of one session (sid8 prefix or UUID). Never raises:
    failures come back as {"sid8"|"ident", "error"}. Cold path = one claude -p
    call (~20-30s); warm path = cache read."""
    try:
        path = find_session(ident)
    except InterrogateError as e:
        return {"ident": ident, "error": str(e)}
    sid8 = path.stem[:8]
    try:
        st = path.stat()
    except OSError as e:
        return {"sid8": sid8, "error": f"stat failed: {e}"}

    cache = None if force else _read_cache(sid8)
    if cache and cache.get("uuid") == path.stem and cache.get("schema_version") == SCHEMA_VERSION:
        cached_bytes = cache.get("jsonl_bytes", -1)
        try:
            age_s = time.time() - datetime.fromisoformat(cache["as_of"]).timestamp()
        except (KeyError, ValueError):
            age_s = None
        if cached_bytes == st.st_size:
            return _public(cache, cached=True, stale=None if age_s is None else {"age_s": round(age_s)})
        if age_s is not None and age_s < ttl_s:
            return _public(
                cache,
                cached=True,
                stale={"age_s": round(age_s), "bytes_behind": st.st_size - cached_bytes},
            )

    numbered, flat, coverage, n_tail, n_total = _tail(path)
    if not numbered.strip():
        return {"sid8": sid8, "error": "empty transcript after extraction"}
    t0 = time.time()
    raw = text_via_max(
        SYSTEM_PROMPT, _fence(numbered), model=model, timeout=timeout, cwd="/tmp"
    )
    if raw is None:
        return {
            "sid8": sid8,
            "error": "mapper returned no answer (claude -p failed/timed out; not cached)",
        }
    claims, t1 = _grounded_claims(raw, flat)
    rec = {
        "schema_version": SCHEMA_VERSION,
        "sid8": sid8,
        "uuid": path.stem,
        "as_of": _now_iso(),
        "jsonl_path": str(path),
        "jsonl_bytes": st.st_size,
        "jsonl_mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(
            timespec="seconds"
        ),
        "coverage": coverage,
        "tail_lines": n_tail,
        "total_lines": n_total,
        "mapper_model": model,
        "wall_s": round(time.time() - t0, 1),
        "t1": t1,
        "claims": claims,
        "raw": raw,  # cache-only (audit trail); stripped from returns
    }
    _write_cache(sid8, rec)
    return _public(rec, cached=False, stale=None)


def fleet_gists(
    idents: list[str],
    *,
    model: str = DEFAULT_MODEL,
    ttl_s: float = DEFAULT_TTL_S,
    max_workers: int = 3,
) -> dict:
    """Gist several sessions concurrently (fail-soft per session). Returns
    {sid8_or_ident: gist_dict}. Bounded workers: cold gists are real LLM
    calls — 3 wide keeps a 6-session fleet under ~a minute."""
    if not idents:
        return {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        results = list(ex.map(lambda i: gist(i, model=model, ttl_s=ttl_s), idents))
    return {r.get("sid8") or r.get("ident", "?"): r for r in results}


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Citation-anchored working-state gist of one session (rung-2 tail digest)."
    )
    ap.add_argument("session", help="sid8 prefix or full UUID")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--ttl", type=float, default=DEFAULT_TTL_S)
    ap.add_argument("--force", action="store_true", help="bypass + rebuild cache")
    ap.add_argument("--json", action="store_true", help="raw JSON out")
    args = ap.parse_args()
    g = gist(args.session, model=args.model, ttl_s=args.ttl, force=args.force)
    if args.json:
        print(json.dumps(g, indent=1))
        return
    if g.get("error"):
        sys.exit(f"[session_digest] {g['error']}")
    hdr = (
        f"gist {g['sid8']} · as_of {g['as_of']} · {g['coverage']} "
        f"({g['tail_lines']}/{g['total_lines']} lines) · {g['mapper_model']}"
        f" · cached={g['cached']} stale={g['stale']}"
    )
    print(hdr)
    print("-" * len(hdr))
    for i, c in enumerate(g["claims"], 1):
        tag = "✓" if c["grounded"] else ("~" if c["cite"] else "∅")
        print(f"[{i}] {tag} {c['text']}")
        if c["cite"]:
            print(f"      cite: {c['cite']}")
    t = g["t1"]
    print(f"-- T1: {t['grounded']} cited · {t['inference']} inference · {t['bad']} bad-cite --")


if __name__ == "__main__":
    main()
