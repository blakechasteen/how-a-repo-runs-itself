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

SIGNED EMISSION (added 2026-07-25, Blake-directed). `record` additionally emits
the disposition as a signed, chained peer-owned bobbin via
`tools/disposition_sign.py` — the same judgment, but existing in the substrate as
an act by an identified party rather than as JSON *about* one. That is the gap
`project_ai_side_substrate_primitives` calls policy-vs-property: sessions decline
and reshape briefs constantly, and until now none of it was signed, so the peer
corpus held only smoke tests, rigs and exception handlers. Signing is default-on
(`--no-sign` opts out) and fail-soft in every direction — an unsigned event is
still a recorded event, and the guardrails above are unchanged: recording is
still opt-in, still never blocking, still WITNESS not KPI.

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
        --kind reshaped|declined|deferred|accepted|bounced --why "..." --sid8 <you> \\
        [--into <successor-brief.md>] [--no-note]
    # read the records back (read-only view + aggregate)
    ./.venv/bin/python tools/brief_disposition.py list [--json]

`bounced` additionally appends a one-line `_Bounced (…)` note to the brief body
(the payload has to land where the next reader reads — brief_bounced_disposition.md
option (b)); `--no-note` suppresses that shared-file write.
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
# free-acceptance marker (rare/opt-in — it de-conflates `consumed`);
# `bounced` = accepted and ATTEMPTED, the attempt died (approach disproven,
# blocked at merge, budget exhausted) — the brief stays `open` (the proposal
# didn't fail, the attempt did), so it is an event no status can carry, and the
# census's drainability cut would otherwise file a twice-bounced brief under
# `ready` exactly as fresh as an untried one. The why names three things: what
# was tried / where it died / the PREMISE that killed it — so a later session
# can see when the premise changed and the approach legitimately revives. A
# bounce informs; it never forbids a re-try, never reassigns, never auto-flips.
KINDS = ("reshaped", "declined", "deferred", "accepted", "bounced")


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


# --- the bounce body-note (option (b): route the payload to where it is read) --
#
# An event record alone closes the RECORDING gap and not the READING one — a
# session picking a brief up Reads the brief, and has no reason to look in
# handoff/brief_dispositions/. So a bounce also appends one line to the brief
# body, mirroring the established `_Lifecycle (…)` idiom: visible on Read,
# greppable, parseable later.
#
# ANTI-FOOTGUN — the grammar is `_Bounced`, deliberately NOT `_Lifecycle`.
# brief_disposition_census._LIFECYCLE_RE matches `^\s*_Lifecycle (…): status A → B`
# and feeds _terminal_date(); writing a bounce as a fake status flip would corrupt
# terminal-date inference for that brief. `_Bounced` is invisible to that regex by
# construction (different literal token).
_BOUNCE_NOTE_PREFIX = "_Bounced ("
_WHY_MAX = 240


def brief_dir() -> Path:
    return Path(os.environ.get(
        "HOLOLOOM_BRIEF_DIR",
        str(Path(__file__).resolve().parent.parent / "handoff" / "brief"),
    ))


def _resolve_brief(brief: str, bdir: Optional[Path] = None) -> Optional[Path]:
    """Bare name / relative / absolute → the brief file, or None (mirrors brief_sweep)."""
    p = Path(brief)
    if p.is_absolute() and p.is_file():
        return p
    cand = (bdir or brief_dir()) / p.name
    if cand.is_file():
        return cand
    rel = Path.cwd() / brief
    return rel if rel.is_file() else None


def _contended_elsewhere(path: Path) -> bool:
    """True if this path is dirty in a DIFFERENT worktree (merge-collision class).

    Best-effort: reuses fleet_view's read-only git helpers. On ANY failure it
    returns False (write proceeds) — this surface is never-blocking, and the
    pre-existing repo norm (brief_sweep.py flip) does no check at all, so an
    unavailable signal must not become a new hard gate."""
    try:
        tools_dir = str(Path(__file__).resolve().parent)
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        import fleet_view  # noqa: E402  (lazy; tolerate git/env unavailable)

        here = path.resolve()
        root = fleet_view._git_toplevel(here.parent)
        worktrees = fleet_view._worktrees(root)
        # which worktree holds MY copy? (the longest root that is a parent of it)
        # (string prefix rather than Path.is_relative_to — 3.9-safe, and worktrees
        # nest, so the LONGEST matching root is the owner)
        mine = ""
        for wt in worktrees:
            wpath = wt.get("path", "")
            if not wpath:
                continue
            wroot = str(Path(wpath).resolve())
            if str(here).startswith(wroot + os.sep) and len(wroot) > len(mine):
                mine = wroot
        if not mine:
            return False  # can't locate it in the worktree set — don't invent a gate
        rel_me = str(here.relative_to(Path(mine)))
        for wt in worktrees:
            wpath = wt.get("path", "")
            if not wpath or str(Path(wpath).resolve()) == mine:
                continue  # my own tree being dirty is expected, not contention
            if rel_me in fleet_view._dirty_paths(wpath):
                return True
        return False
    except Exception:
        return False


def append_bounce_note(brief: str, why: str, sid8: str,
                       bdir: Optional[Path] = None,
                       now: Optional[_dt.datetime] = None,
                       check_contention: bool = True) -> Optional[Path]:
    """Append one `_Bounced (<date>, sid8 <sid8>): <why>_` line to the brief body.

    Returns the brief path on write, None otherwise (not found, contended,
    already recorded today by this session, or any failure). NEVER RAISES —
    same never-blocking contract as record(); a body note that can't be written
    must not cost the caller its event record.
    """
    try:
        path = _resolve_brief(brief, bdir)
        if path is None:
            _warn(f"brief_disposition: no such brief {brief!r} — event recorded, body note skipped")
            return None
        if check_contention and _contended_elsewhere(path):
            _warn(f"brief_disposition: {path.name} is dirty in another worktree — "
                  "body note skipped (event record still written)")
            return None
        dt = now or _dt.datetime.now(_dt.timezone.utc)
        one_line = " ".join((why or "").split())
        if len(one_line) > _WHY_MAX:
            one_line = one_line[:_WHY_MAX - 1].rstrip() + "…"
        sid = f", sid8 {sid8}" if sid8 else ""
        note = f"{_BOUNCE_NOTE_PREFIX}{dt.date().isoformat()}{sid}): {one_line}_"
        text = path.read_text()
        if note in text:
            return None  # idempotent: identical bounce already on the file
        out = text if text.endswith("\n") else text + "\n"
        out += f"\n{note}\n"
        # atomic (temp + os.replace) — a concurrent Reader never sees a half file
        tmp = path.parent / f".{path.name}.{os.getpid()}.tmp"
        tmp.write_text(out)
        os.replace(str(tmp), str(path))
        # parse-verify (frontmatter-normalizer discipline): the note landed AND
        # the frontmatter fence is still intact (we only append, but verify anyway).
        v = path.read_text()
        if note not in v or not v.lstrip().startswith("---"):
            _warn(f"brief_disposition: WARNING — post-write verify failed on {path.name}")
            return None
        return path
    except Exception as e:  # noqa: BLE001 — never-blocking surface
        _warn(f"brief_disposition: bounce note failed ({type(e).__name__}: {e})")
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
        "note": ("opt-in FLOOR, not a total — only volunteered records. reshaped, "
                 "deferred and bounced are invisible to the lifecycle census (a "
                 "bounced brief stays `open`); this is the only place they "
                 "surface. WITNESS not KPI."),
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
    # A bounce ALSO leaves the one-line note on the brief itself — the next
    # session picking the brief up reads the brief, not this records dir. Kept
    # out of record() on purpose: the library call stays confined to its own
    # append-only dir, and the shared-file write is explicit at the CLI layer.
    # Fail-soft: a skipped note never fails the command (the event is recorded).
    if args.kind == "bounced" and not args.no_note:
        n = append_bounce_note(args.brief, args.why, args.sid8)
        if n is not None:
            print(f"  + _Bounced note appended to {n.name}")
    # …and the disposition is ALSO emitted as a signed peer-owned bobbin, so the
    # judgment exists in the substrate as an act by an identified party, not only
    # as JSON about one. Same placement reasoning as the bounce note: an outward
    # side effect (it extends a chain and posts to the Matrix transparency log)
    # belongs at the CLI layer, never inside record().
    #
    # Default-ON with an escape hatch, deliberately: an opt-in inside an opt-in
    # would never be exercised, and an unexercised refusal channel is precisely
    # the thing this closes. Import is lazy so this module stays stdlib-only.
    # Fail-soft — an unsigned event is still a recorded event.
    if not args.no_sign:
        try:
            import disposition_sign
        except Exception:  # noqa: BLE001 — signing is additive, never required
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            try:
                import disposition_sign  # noqa: F811
            except Exception as e:  # noqa: BLE001
                _warn(f"brief_disposition: signing unavailable ({type(e).__name__}: {e})")
                return 0
        sig = disposition_sign.sign(
            args.brief, args.kind, args.why, args.sid8,
            reshaped_into=args.into, record_file=p.name)
        if sig:
            print(f"  + signed as {sig['peer']}/{sig['bobbin_kind']}/{sig['slug']}"
                  + (f" (chain seq {sig['chain_seq']})" if sig.get("chain_seq") else ""))
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
          f"deferred {bk['deferred']}  |  accepted {bk['accepted']}  |  "
          f"bounced {bk['bounced']}"
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
    r.add_argument("--no-note", action="store_true",
                   help="bounced only: skip the `_Bounced (…)` body note on the brief "
                        "(event record still written)")
    r.add_argument("--no-sign", action="store_true",
                   help="skip the signed peer-bobbin emission (event record still "
                        "written). Signing is default-on; see tools/disposition_sign.py")

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
