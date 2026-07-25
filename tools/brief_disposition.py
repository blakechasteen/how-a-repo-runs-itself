#!/usr/bin/env python3
"""brief_disposition.py — opt-in engagement-event record for workplan briefs.

Option B of handoff/brief/brief_decline_visibility.md (greenlit by Blake
2026-07-05). The disposition census (tools/brief_disposition_census.py) measures
the WSH engagement invariant from data already on disk, but two things it CANNOT
see are events, not lifecycle states:

  * RESHAPE — the convention names accept/reshape/decline, but the lifecycle has
    states for only consumed/declined/superseded. A brief accepted-*with-
    modification* (the middle, most common, most healthy outcome) flips to
    `consumed` and leaves no distinct trace.
  * The structured, aggregable WHY — a decline's reason is per-file free text
    buried in one frontmatter; ~55% of terminal dispositions carry no structured
    why at all (census flip-instrumentation).

This module is the thin capture surface for exactly those two. It writes a small
append-only event record — `handoff/brief_dispositions/<ts>__<slug>__<sid8>.json`
— mirroring the `handoff/reattestations/` pattern (same filename grammar, same
`{kind, advisory, note, ...}` envelope). The census reads these back so reshape
becomes a real (opt-in *floor*) count and the whys aggregate.

    THE HARD GUARDRAILS (from the brief — the ones that keep the fix from
    becoming the disease):
    - **Opt-in / never blocking.** Recording a disposition is NEVER a mandatory
      handoff step. If *not doing* a suggested thing became bureaucratically
      expensive to record, sessions would drift toward just doing briefs —
      rebuilding the task queue the WSH invariant exists to prevent. `record()`
      fail-soft-returns None on any error; it must never abort a caller.
    - **WITNESS, never a KPI.** No decline/reshape-rate target. The count is a
      floor (only volunteered records), reported as a mix, never optimized.
    - **Structural, not algorithmic.** A narrowed channel contract, not an
      engagement score. No per-brief scoring, ranking, or nudges — this module
      records what a session volunteers and reads it back; it never prompts.
    - **Surfacing, not deciding.** It records; it judges nothing.

Sibling to the fifth_discipline `suspended:` idea (record what a pass GAVE UP,
not only its verdict): a decline/defer `why` is the same shape — what was set
aside and the reason, so team-learning doesn't evaporate.

Design note: this is deliberately a STANDALONE tool, not a new `brief_sweep.py`
subcommand (the brief suggested the latter). A disposition *event* is a distinct
concern from a lifecycle *flip* (brief_sweep is "candidate surfacer + safe status
flip"), and at build time a concurrent session held `worktree:brief-sweep-flip-2`
— editing brief_sweep.py would have risked a namespace/merge collision. It can be
folded in later if that reads cleaner (suggestion-not-directive, reshaped).

Read-only except for its own append-only records dir. Dependency-free (stdlib),
Python-3.9-compatible, fail-CLOSED on read (a malformed record is surfaced in a
`malformed` bucket, never silently dropped).

Usage:
    # record an engagement event (opt-in; run when you reshape/decline/defer a brief)
    ./.venv/bin/python tools/brief_disposition.py record <brief.md> \\
        --kind reshaped|declined|deferred|accepted --why "..." --sid8 <you> \\
        [--into <successor-brief.md>]
    # read the records back (read-only view + aggregate)
    ./.venv/bin/python tools/brief_disposition.py list [--json]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

# The engagement events this surface captures. `reshaped`/`deferred` have NO
# lifecycle status (the whole point — they're invisible to the census otherwise);
# `declined` mirrors a status the brief may ALSO flip (the record adds the
# aggregable why the flip note can't); `accepted` is an optional explicit
# free-acceptance marker (rare/opt-in — it de-conflates `consumed`).
KINDS = ("reshaped", "declined", "deferred", "accepted")


def dispositions_dir() -> Path:
    return Path(os.environ.get(
        "HOLOLOOM_DISPOSITIONS_DIR",
        str(Path(__file__).resolve().parent.parent / "handoff" / "brief_dispositions"),
    ))


def _slug(brief: str) -> str:
    """Brief filename → a filename-safe slug for the record name (stem, no .md)."""
    stem = Path(brief).name
    if stem.endswith(".md"):
        stem = stem[:-3]
    return re.sub(r"[^A-Za-z0-9._-]", "-", stem) or "brief"


def _warn(msg: str) -> None:
    """Best-effort stderr warning that NEVER raises. A broken/closed stderr
    (realistic under launchd / git-hook plumbing) must not turn this opt-in,
    never-blocking surface into a caller-aborting one — so even the warning
    swallows its own failure."""
    try:
        print(msg, file=sys.stderr)
    except Exception:
        pass


def record(brief: str, kind: str, why: str, sid8: str,
           reshaped_into: Optional[str] = None,
           ddir: Optional[Path] = None,
           now: Optional[_dt.datetime] = None) -> Optional[Path]:
    """Append one disposition event record; return its path (None on any failure).

    NEVER RAISES — the whole surface is opt-in / non-blocking, so a write problem
    (bad kind, unwritable dir) must degrade to a stderr warning + None, never
    abort the caller. `now` is injectable for deterministic tests.
    """
    try:
        if kind not in KINDS:
            _warn(f"brief_disposition: unknown kind {kind!r} (want {'/'.join(KINDS)})")
            return None
        ddir = ddir or dispositions_dir()
        dt = now or _dt.datetime.now(_dt.timezone.utc)
        ts_file = dt.strftime("%Y-%m-%dT%H-%M-%SZ")   # filename grammar (mirror reattest)
        rec = {
            "kind": "brief_disposition",
            "advisory": True,
            "note": ("ADVISORY / opt-in engagement record — never gates a brief, "
                     "never mandatory. Captures the accept/reshape/decline "
                     "negotiation the 4-state lifecycle can't (reshape has no "
                     "status; consumed conflates freely-accepted vs obligated). "
                     "WITNESS not KPI."),
            "brief": Path(brief).name,
            "disposition": kind,
            "sid8": sid8 or "",
            "date": dt.date().isoformat(),
            "recorded_at": dt.isoformat(),
            "why": why or "",
        }
        if reshaped_into:
            rec["reshaped_into"] = Path(reshaped_into).name
        ddir.mkdir(parents=True, exist_ok=True)
        # Collision-safe (append-only, never overwrite): two events for the same
        # brief+sid8 within one second get a -N suffix so neither is lost. Same
        # session is single-process, and different sessions have distinct sid8, so
        # the free-name scan has no cross-process race in practice.
        base = f"{ts_file}__{_slug(brief)}__{sid8 or 'nosid'}"
        path = ddir / f"{base}.json"
        _n = 2
        while path.exists():
            path = ddir / f"{base}-{_n}.json"
            _n += 1
        # Atomic write (temp + os.replace): a concurrent reader never catches a
        # half-written file, and a partial/failed write can't leave a malformed
        # `.json` turd at the final name (the leftover `.tmp` is dot-hidden and
        # not matched by the reader's *.json glob).
        payload = json.dumps(rec, indent=2) + "\n"
        tmp = ddir / f".{base}.{os.getpid()}.tmp"
        tmp.write_text(payload)
        os.replace(str(tmp), str(path))
        # parse-verify (cf. frontmatter-normalizer discipline: confirm we didn't
        # write garbage) — fail-soft.
        json.loads(path.read_text())
        return path
    except Exception as e:  # noqa: BLE001 — opt-in surface: warn, never abort caller
        _warn(f"brief_disposition: record failed ({type(e).__name__}: {e})")
        return None


def load_records(ddir: Optional[Path] = None) -> dict:
    """Read all disposition records. READ-ONLY, fail-CLOSED: an unreadable/invalid
    record file is surfaced in `malformed`, never silently dropped.

    Returns {records: [dict, ...], malformed: [name, ...]}.
    """
    ddir = ddir or dispositions_dir()
    out = {"records": [], "malformed": []}
    if not ddir.is_dir():
        return out
    for f in sorted(ddir.glob("*.json")):
        try:
            rec = json.loads(f.read_text())
            if not isinstance(rec, dict) or "disposition" not in rec:
                out["malformed"].append(f.name)
                continue
            rec.setdefault("_file", f.name)
            out["records"].append(rec)
        except Exception:
            out["malformed"].append(f.name)   # fail-closed — flagged, not hidden
    return out


def summarize(loaded: dict) -> dict:
    """Aggregate loaded records into the census-facing shape. Pure (no I/O)."""
    recs = loaded.get("records", [])
    by_kind = {k: 0 for k in KINDS}
    other_kind = 0
    by_brief: dict = {}
    whys: list = []
    for r in recs:
        k = str(r.get("disposition") or "").strip()
        if k in by_kind:
            by_kind[k] += 1
        else:
            other_kind += 1
        b = str(r.get("brief") or "?")
        by_brief[b] = by_brief.get(b, 0) + 1
        if r.get("why"):
            whys.append({"brief": b, "kind": k, "sid8": r.get("sid8", ""),
                         "date": r.get("date", ""), "why": r.get("why", ""),
                         "reshaped_into": r.get("reshaped_into")})
    return {
        "n": len(recs),
        "by_kind": by_kind,
        "other_kind": other_kind,
        "malformed_n": len(loaded.get("malformed", [])),
        "malformed": loaded.get("malformed", []),
        # neutral (name) sort, NOT count-descending: a per-brief *ranking* is the
        # leaderboard shape the guardrail forbids (structural-not-algorithmic). This
        # is a raw count map, ordered by name so it never reads as a score.
        "by_brief": dict(sorted(by_brief.items())),
        "whys": whys,
        "note": ("opt-in FLOOR, not a total — only volunteered records. reshaped + "
                 "deferred are invisible to the lifecycle census; this is the only "
                 "place they surface. WITNESS not KPI."),
    }


def reshaped_recorded_count(ddir: Optional[Path] = None) -> int:
    """Cheap reshaped-event count for the fleet headline (glob-count of the
    `reshaped` kind). Fail-soft to 0; never raises."""
    try:
        return summarize(load_records(ddir))["by_kind"]["reshaped"]
    except Exception:
        return 0


# --- CLI ---------------------------------------------------------------------

def _cmd_record(args) -> int:
    p = record(args.brief, args.kind, args.why, args.sid8,
               reshaped_into=args.into)
    if p is None:
        return 1
    print(f"recorded {args.kind} disposition for {Path(args.brief).name} → {p}")
    return 0


def _cmd_list(args) -> int:
    loaded = load_records()
    summ = summarize(loaded)
    if args.json:
        print(json.dumps(summ, indent=2))
        return 0
    print(f"Brief dispositions — {summ['n']} record(s) "
          f"(opt-in floor; WITNESS not KPI)")
    bk = summ["by_kind"]
    print(f"  reshaped {bk['reshaped']}  |  declined {bk['declined']}  |  "
          f"deferred {bk['deferred']}  |  accepted {bk['accepted']}"
          + (f"  |  other {summ['other_kind']}" if summ["other_kind"] else "")
          + (f"  |  MALFORMED {summ['malformed_n']}" if summ["malformed_n"] else ""))
    if summ["whys"]:
        print("  whys (what was set aside + reason):")
        for w in summ["whys"]:
            into = f"  → {w['reshaped_into']}" if w.get("reshaped_into") else ""
            print(f"    • [{w['kind']}] {w['brief']} ({w['date']}, {w['sid8']}): "
                  f"{w['why'][:140]}{into}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Opt-in engagement-event record for workplan briefs (reshape/decline/defer + why).")
    sub = ap.add_subparsers(dest="cmd")

    r = sub.add_parser("record", help="append one disposition event (opt-in, never-blocking)")
    r.add_argument("brief", help="brief filename (e.g. brief_decline_visibility.md)")
    r.add_argument("--kind", required=True, choices=list(KINDS))
    r.add_argument("--why", default="", help="what was set aside/changed and why (aggregable)")
    r.add_argument("--sid8", default="", help="recording session (first 8 of $CLAUDE_CODE_SESSION_ID)")
    r.add_argument("--into", default="", help="successor brief filename, if a reshape spun one out")

    l = sub.add_parser("list", help="read records back (read-only view + aggregate)")
    l.add_argument("--json", action="store_true")

    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in ("record", "list", "-h", "--help"):
        # bare invocation → list (read-only default, mirrors brief_sweep)
        argv = ["list", *argv]
    args = ap.parse_args(argv)
    if args.cmd == "record":
        return _cmd_record(args)
    return _cmd_list(args)


if __name__ == "__main__":
    raise SystemExit(main())
