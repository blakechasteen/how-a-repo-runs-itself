#!/usr/bin/env python3
"""brief_sweep.py — the missing brief-lifecycle collector.

"Tail-call elimination for the governance stack." The brief queue
(handoff/brief/*.md) has a base case in its schema (done_when + the
open→consumed/declined/superseded lifecycle) but no actor that evaluates it,
so it accumulates — open briefs grow while nothing pops them. This is that
actor, run as a /handoff step.

It is a *candidate surfacer*, not an auto-popper, for a reason grounded in the
data: done_when is almost always a prose judgment predicate ("...OR explicitly
declined with reason"), not a machine predicate. Auto-flipping a brief to
`consumed` when the work isn't actually done is worse than leaving it open, and
auto-`declined` silently kills a suggestion the receiving session was meant to
negotiate — which would convert the brief queue into the task queue the
convention's one load-bearing property ("suggestion, not directive") forbids.
So the collector identifies the frames that *can* pop by cheap, honest signals
and leaves the pop to the session/human (confirm-to-flip). Lifecycle stays
manual; this only adds the missing prompt.

Subcommands:
  report (default)  READ-ONLY. Surface retirement candidates + the signal each
                    fired on. Decides nothing. Every run footers a one-line
                    backstop-coverage tally; `report --needs-backstop` switches
                    to a lint listing the open briefs that carry no dated auto-
                    decline clause (WSH decay-vent slice A — surfacer, not a gate).
  flip <file>       Apply one confirmed lifecycle flip (status + a dated body
                    note), preserving frontmatter/provenance. The session calls
                    this only AFTER confirming — so the LLM never hand-edits
                    frontmatter (cf. feedback_memory_edit_frontmatter_normalizer).

Signals (all cheap, deterministic, no LLM, no DB):
  done_when_verdict  EVERY open brief's done_when, classified fail-closed by
                `done_when_eval` (Pinsmith slice 1) into {time-expiry | numeric-
                threshold | prose-judgment | manual} with a verdict. Context-tier
                (weight 0): a `needs_attestation` verdict NEVER becomes a retire
                candidate — only the one auto-evaluable case below does.
  expired       done_when carries an AUTHORED time-expiry clause ("untouched by
                YYYY-MM-DD", "by YYYY-MM-DD … declined") whose date has passed →
                strong `declined` candidate (the author opted into auto-expiry).
                Now sourced from `done_when_eval.classify` (single source of
                truth), not a second inline regex.
  ratify_ready  a proposal brief (claudemd_ structural OR any brief with a
                `proposal_target` — e.g. slice-6 consolidation_ proposals) whose
                cooling_off_until has elapsed → not a retire, an action ("ready
                to ratify"). Generalized so the consolidation→proposal pipeline's
                cooling-off is surfaced too, not just CLAUDE.md amendments.
  touched       the brief's topic/title tokens intersect files this session
                touched (SESSION.json files_touched) → the work may have just
                happened; review for consumed.
  stale         created > --stale-days ago AND untouched in git since → review
                whether still live.
  (info only)   a future time-expiry date, or a numeric threshold in done_when
                (e.g. "pin count ≥ 300"), is carried by done_when_verdict as
                context, not a candidate.

Dependency-free (stdlib only); frontmatter parsing mirrors server.py's tolerant
_parse_brief_frontmatter so the sweep and orient agree on what an open brief is.
The done_when *predicate* itself is read by `done_when_eval.read_done_when`,
which (unlike the flat mirror parser) handles YAML block scalars (`done_when: >`).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

# sibling modules — done_when classification (Pinsmith slice 1) + the shared
# strict-compatible frontmatter reader. tools/ is on sys.path[0] when this runs
# as `tools/brief_sweep.py`; tests put it on the path.
import done_when_eval
import frontmatter

# --- frontmatter (shared reader; server.py delegates to the same module) ------

def parse_frontmatter(text: str) -> Optional[dict]:
    """Leading ---fenced block → flat dict of scalar/`[a,b]` entries. None if
    no fence. Delegates to tools/frontmatter.py — the one strict-compatible
    reader (handoff/brief/frontmatter_parser_unify.md) — so orient and the
    sweep classify briefs identically by construction, not by byte-alignment."""
    fm = frontmatter.parse_frontmatter(text, inline_lists=True)
    return fm or None


def brief_dir() -> Path:
    return Path(os.environ.get(
        "HOLOLOOM_BRIEF_DIR",
        str(Path(__file__).resolve().parent.parent / "handoff" / "brief"),
    ))


def iter_open_briefs(bdir: Path):
    """Yield (path, fm) for files orient would surface as open briefs: skip
    `_`-prefixed meta, skip non-open, skip missing done_when. Same gate as
    server._compose_workplan_briefs (minus the topic/global surfacing filter —
    the sweep looks at *all* open briefs, not just advertised ones)."""
    if not bdir.is_dir():
        return
    for path in sorted(bdir.glob("*.md")):
        if path.name.startswith("_"):
            continue
        try:
            fm = parse_frontmatter(path.read_text())
        except Exception:
            continue
        if not fm or fm.get("status", "open") != "open":
            continue
        if not fm.get("done_when"):
            continue  # malformed; orient skips it too
        yield path, fm


# --- signal helpers ----------------------------------------------------------

# done_when classification (time-expiry / numeric-threshold detection) moved to
# done_when_eval — single source of truth, block-scalar-aware, fail-closed.


def _date(s: str) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(s)
    except Exception:
        return None


def _attestation_verdicts(text: str) -> list[str]:
    """Lower-cased `verdict:` values from the `attestations:` frontmatter block.

    The flat `parse_frontmatter` above can't descend the nested attestations list
    (it collapses to a scalar), so scan the fenced block directly — dependency-free,
    no yaml import (keeps the module's no-dep posture). Scope to the attestations
    block (a column-0 key other than `attestations:` ends it) so a `done_when: >`
    block-scalar mentioning "verdict" can't leak in. Within the block, match the
    `verdict:` KEY in mapping position only — line-start or after `,`/`{` — so
    ordinary `note:` prose (which routinely uses the words "reshape"/"decline")
    does not false-match. (Residual: a note that *literally* embeds a
    `, verdict: <word>` mapping fragment would match — negligible in practice, and
    the RATIFY label it feeds stays Blake-gated regardless, never auto-flips.)
    Handles both the inline flow form
    (`- {session_id: …, verdict: reshape, note: "…"}`) and a block form
    (`    verdict: approve`). Fail-closed to [] on any malformed input."""
    if not text.startswith("---"):
        return []
    end = text.find("\n---", 3)
    if end == -1:
        return []
    verdicts: list[str] = []
    in_block = False
    for line in text[3:end].splitlines():
        if line[:1] and not line[:1].isspace():       # a column-0 (top-level) key
            in_block = line.strip().startswith("attestations:")
        if in_block:
            verdicts.extend(
                m.lower() for m in re.findall(r"(?:^|[,{])\s*verdict:\s*['\"]?(\w+)", line)
            )
    return verdicts


def _tokens(*vals: str) -> set[str]:
    """Significant (len>=4) topic/title tokens for touch-matching."""
    toks: set[str] = set()
    for v in vals:
        for t in re.split(r"[\s\-_/]+", (v or "").lower()):
            if len(t) >= 4:
                toks.add(t)
    return toks


def _git_last_touch(repo: Path, rel: str) -> Optional[_dt.date]:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%cd",
             "--date=short", "--", rel],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        return _date(out) if out else None
    except Exception:
        return None


def _in_linked_worktree(cwd: Path) -> bool:
    """True when cwd sits in a linked git worktree (git-dir ≠ common-dir).

    Fail-soft to True: outside a repo (or with git unavailable) a plain
    SESSION.json is most plausibly the local session's own scratchpad, so
    the permissive read matches legacy behavior.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--path-format=absolute",
             "--git-dir", "--git-common-dir"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return True
        lines = out.stdout.strip().splitlines()
        if len(lines) < 2:
            return True
        return Path(lines[0]).resolve() != Path(lines[1]).resolve()
    except Exception:
        return True


def _session_touched(cwd: Path) -> tuple[list[str], str]:
    """(files_touched, sid8) from THIS session's live scratchpad, fail-soft.

    Scratchpad resolution (#83 shape 1, sitting 2026-07-02): prefer the
    running session's own `SESSION.<sid8>.json` (sid8 from
    $CLAUDE_CODE_SESSION_ID — main-checkout naming), else plain
    `SESSION.json` (worktree naming / legacy). Never read a PEER's
    per-sid8 file: the old shared SESSION.json was whatever session wrote
    last, which mis-attributed "touched this session" to the wrong
    session's file list (watch-out, 5de56efa). No own scratchpad → no
    touched signal, honestly, rather than a wrong one.

    Two cleanups, both load-bearing for the `touched` signal's precision:
      - Strip descriptive suffixes: entries are often "path (new, <sha>)" — keep
        only the path before the first " (", or the parenthetical leaks tokens.
      - Drop META paths (handoff/, SESSION.json, KICKOFF, the brief dir itself).
        Touching a *brief / handoff / session* file is meta-work, not topic-work
        on what that brief is about — and matching brief topics against OTHER
        briefs' paths fired 21/49 false positives (generic shared tokens like
        'canon'/'recall'). The signal is meant to catch "you worked the SOURCE
        this brief is about", so meta paths must not participate.
    """
    own_sid = (
        os.environ.get("CLAUDE_CODE_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
        or ""
    )[:8]
    sj = None
    if own_sid:
        cand = cwd / f"SESSION.{own_sid}.json"
        if cand.is_file():
            sj = cand
        elif not _in_linked_worktree(cwd):
            # Own sid known, own file absent, shared main checkout: a plain
            # SESSION.json here is a peer's / stale — no signal beats a
            # wrong one.
            return [], ""
    if sj is None:
        cand = cwd / "SESSION.json"
        if cand.is_file():
            sj = cand
    if sj is None:
        return [], ""
    try:
        d = json.loads(sj.read_text())
        clean: list[str] = []
        for entry in (d.get("files_touched") or []):
            p = str(entry).split(" (")[0].strip()
            low = p.lower()
            if (low.startswith("handoff/") or "/handoff/" in low
                    or "session.json" in low or "kickoff" in low):
                continue
            clean.append(p)
        return clean, str(d.get("sid8") or "")
    except Exception:
        return [], ""


def compute_signals(path: Path, fm: dict, today: _dt.date, repo: Path,
                    touched: list[str]) -> list[dict]:
    sigs: list[dict] = []
    name = path.name

    # done_when verdict (fail-closed; single source of truth = done_when_eval).
    # Read the REAL predicate (block-scalar aware), not the flat fm value which
    # collapses a folded `done_when: >` to the bare marker ">".
    try:
        real_dw = done_when_eval.read_done_when(path.read_text())
    except Exception:
        real_dw = None
    real_dw = real_dw or (fm.get("done_when", "") or "")
    v = done_when_eval.classify(real_dw, today)
    sigs.append({"kind": "done_when_verdict", "weight": 0, "to": v.to, "cls": v.cls,
                 "evidence": f"done_when {done_when_eval.DISPLAY.get(v.cls, v.cls)} "
                             f"→ {v.verdict}: {v.evidence}"})
    # The ONLY retire candidate done_when can produce: an AUTHORED time-expiry
    # the author wrote that has now passed (they opted into auto-retirement).
    if v.cls == "time_expiry" and v.verdict == "met":
        sigs.append({"kind": "expired", "weight": 4, "to": v.to or "declined",
                     "evidence": v.evidence})

    # ratify_ready — a proposal brief past cooling-off. Generalized from
    # claudemd_-only to ANY brief carrying a proposal_target (so slice-6
    # consolidation_ proposals surface their elapsed cooling-off too).
    #
    # RATIFY-READY must READ THE ATTESTATION RECORD, not just cooling-off
    # (brief_sweep_ratify_ready_verdict_check, sid8 5cf4e7e4). The amendment
    # procedure defines ready-to-ratify as ">=1 distinct-session APPROVE AND
    # cooling-off elapsed"; a cooling-off-only label once printed RATIFY-READY for
    # a proposal whose sole attestation was a *reshape* (claudemd_proof_block,
    # 2026-07-02), claiming a procedural state the record didn't support. The label
    # now names what the record actually says. Still a SURFACER, not a decider:
    # every branch is weight-3 (surfaced) + to=None (never auto-flips) — Blake
    # disposes. This narrows the label's CONTRACT to the record; it adds no scoring.
    co = _date(fm.get("cooling_off_until", "") or "")
    if (name.startswith("claudemd_") or fm.get("proposal_target")) and co:
        if co <= today:
            verdicts = _attestation_verdicts(path.read_text())
            vset = set(verdicts)
            if "approve" in vset:
                n = verdicts.count("approve")
                sigs.append({"kind": "ratify_ready", "weight": 3, "to": None,
                             "evidence": f"cooling-off elapsed {co} + {n} approve attestation(s) "
                                         f"→ ready to ratify (Blake-gated)"})
            elif vset:
                # attestations exist but NONE approve — name the verdict(s); a
                # ratify here is Blake's informed OVERRIDE, not the procedure's own
                # recommendation. Distinct label per the finding's fix shape.
                named = ",".join(sorted(vset))
                kind = ("attested_reshape" if vset == {"reshape"}
                        else "attested_decline" if vset == {"decline"}
                        else "attested_no_approve")
                sigs.append({"kind": kind, "weight": 3, "to": None,
                             "evidence": f"cooling-off elapsed {co}; attestations are {named}-only "
                                         f"(no approve) → Blake-gated OVERRIDE, not procedure-ready"})
            else:
                sigs.append({"kind": "cooling_elapsed_unattested", "weight": 3, "to": None,
                             "evidence": f"cooling-off elapsed {co}, no attestations yet "
                                         f"→ needs >=1 distinct-session approve"})
        else:
            sigs.append({"kind": "info", "weight": 0, "to": None,
                         "evidence": f"cooling-off until {co} (in {(co - today).days}d)"})

    # touched — brief tokens intersect files this session touched
    # as_text: `topic: [a, b]` parses to a real list under inline_lists, which
    # _tokens' .lower() cannot take (it broke the census the same way). sep=" "
    # on purpose — _tokens splits on whitespace, so the default ", " would glue a
    # comma onto the first slug ('alpha,') and it would match no filename.
    toks = _tokens(frontmatter.as_text(fm.get("topic"), sep=" "),
                   fm.get("title", ""), path.stem)
    hits = sorted({f for f in touched for t in toks if t in f.lower()})
    if hits:
        ev = ", ".join(hits[:3]) + (" …" if len(hits) > 3 else "")
        sigs.append({"kind": "touched", "weight": 2, "to": "consumed?",
                     "evidence": f"touched this session: {ev}"})

    # stale — old AND untouched in git since creation
    created = _date(fm.get("created", "") or "")
    if created:
        age = (today - created).days
        last = _git_last_touch(repo, str(path.relative_to(repo)))
        untouched = (last is None) or (last <= created)
        if age > STALE_DAYS and untouched:
            sigs.append({"kind": "stale", "weight": 1, "to": "review",
                         "evidence": f"open {age}d, untouched since created"})

    return sigs


STALE_DAYS = 45


# --- backstop lint (WSH decay-vent slice A) ----------------------------------
#
# A brief "has a backstop" iff its done_when carries a dated auto-decline clause
# — i.e. done_when_eval.classify() returns cls == 'time_expiry'. That is the ONLY
# class the sweep can auto-surface as EXPIRED (compute_signals above), so a brief
# lacking it never reaches the author-opted auto-retirement path; it falls only to
# the coarse >45d `stale` heuristic. The lint COUNTS + LISTS the gap so the norm
# ("every new brief SHOULD carry a dated auto-decline") can spread by surfacing,
# not by a required field. Read-only; decides nothing — a genuinely human-gated
# brief may stay backstop-less by choice, this just makes the choice visible.
# Def is byte-aligned with done_when_eval (single source of truth), NOT the coarse
# grep proxy in the brief's done_when — classify won't false-count a brief that
# merely says "backstop"/"tripwire" in prose without a dated clause.

_BACKSTOP_HINT = {
    "prose_judgment": "softest; a dated backstop is the cheapest safety net",
    "numeric_threshold": "auto-checks a metric, but no dated fallback",
    "manual": "human-gated; honest exception, but a date still bounds the wait",
    "unknown": "no parseable done_when — needs a predicate AND a backstop",
}


def _emit_backstop_lint(missing: list, n_open: int, today: _dt.date,
                        as_json: bool) -> int:
    """Render the needs-backstop lint. `missing` is [(path, cls), ...] for open
    briefs whose done_when has no dated auto-decline (cls != time_expiry)."""
    by_cls: dict[str, list[str]] = {}
    for path, cls in missing:
        by_cls.setdefault(cls, []).append(path.stem)
    n_missing = len(missing)
    n_has = n_open - n_missing

    if as_json:
        print(json.dumps({
            "open_total": n_open,
            "has_backstop": n_has,
            "needs_backstop": n_missing,
            "by_class": {done_when_eval.DISPLAY.get(c, c): sorted(v)
                         for c, v in sorted(by_cls.items(), key=lambda kv: (-len(kv[1]), kv[0]))},
        }, indent=2))
        return 0

    if n_missing == 0:
        print(f"Backstop lint: all {n_open} open briefs carry a dated auto-decline. Clean.")
        return 0

    suggest = (today + _dt.timedelta(days=90)).isoformat()
    print(f"Handoff — backstop lint: {n_missing} of {n_open} open briefs carry NO dated "
          f"auto-decline backstop ({n_has} do).")
    print("A dated `untouched by YYYY-MM-DD → declines` clause lets the sweep surface a brief")
    print("as EXPIRED when it goes stale; without one, only the coarse >45d `stale` cut reaches it.\n")
    for cls, stems in sorted(by_cls.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        hint = _BACKSTOP_HINT.get(cls, "")
        print(f"  {done_when_eval.DISPLAY.get(cls, cls)} ({len(stems)}) — {hint}:")
        for stem in sorted(stems):
            print(f"    • {stem}")
    print(f"\nAdd to a brief's done_when (choose a real date; {suggest} ≈ +90d):")
    print(f"    OR untouched by {suggest} → auto-declines")
    print("SURFACER, not a gate: nothing is required. Add backstops where the brief is real;")
    print("a genuinely human-gated brief may stay backstop-less by choice — this just makes it visible.")
    return 0


def _backstop_coverage_line(n_open: int, n_missing: int) -> str:
    n_has = n_open - n_missing
    return (f"Backstop coverage: {n_has}/{n_open} open briefs carry a dated auto-decline; "
            f"{n_missing} need one (run `report --needs-backstop` to list).")


# --- commands ----------------------------------------------------------------

def cmd_report(args) -> int:
    global STALE_DAYS
    STALE_DAYS = args.stale_days
    bdir = brief_dir()
    repo = _repo_root(bdir)
    cwd = Path.cwd()
    touched, sid8 = _session_touched(cwd)
    today = _dt.date.today()

    rows = []
    n_open = 0
    backstop_missing: list = []  # (path, cls) for open briefs w/o a dated auto-decline
    for path, fm in iter_open_briefs(bdir):
        n_open += 1
        allsigs = compute_signals(path, fm, today, repo, touched)
        dwv = next((s for s in allsigs if s["kind"] == "done_when_verdict"), None)
        if dwv is not None and dwv.get("cls") != "time_expiry":
            backstop_missing.append((path, dwv.get("cls", "unknown")))
        sigs = [s for s in allsigs if s["weight"] > 0]    # retire / action candidates
        infos = [s for s in allsigs if s["weight"] == 0]  # context (incl. done_when_verdict)
        if sigs:
            rows.append((path, max(s["weight"] for s in sigs), sigs, infos))
    rows.sort(key=lambda r: r[1], reverse=True)
    n_missing = len(backstop_missing)

    # backstop lint mode (WSH decay-vent slice A) — orthogonal to retirement:
    # a coverage lint over authoring, not a retire candidate. Read-only.
    if args.needs_backstop:
        return _emit_backstop_lint(backstop_missing, n_open, today, args.json)

    if args.json:
        print(json.dumps({
            "open_total": n_open, "candidates": len(rows),
            "session_files_touched": touched,
            "backstop": {
                "has": n_open - n_missing, "needs": n_missing,
                "by_class": {
                    done_when_eval.DISPLAY.get(c, c): n for c, n in sorted(
                        Counter(c for _p, c in backstop_missing).items(),
                        key=lambda kv: (-kv[1], kv[0]))
                },
            },
            "rows": [{"brief": p.name,
                      "signals": [{k: s[k] for k in ("kind", "to", "evidence")} for s in sigs],
                      "info": [s["evidence"] for s in infos]} for p, _, sigs, infos in rows],
        }, indent=2))
        return 0

    if not rows:
        print(f"Handoff — brief sweep: {n_open} open, 0 retirable candidates.")
        print(_backstop_coverage_line(n_open, n_missing))
        return 0

    print(f"Handoff — brief sweep ({len(rows)} of {n_open} open look retirable):")
    label = {"expired": "EXPIRED", "ratify_ready": "RATIFY-READY",
             "attested_reshape": "ATTESTED-RESHAPE",
             "attested_decline": "ATTESTED-DECLINE",
             "attested_no_approve": "ATTESTED-NO-APPROVE",
             "cooling_elapsed_unattested": "COOLING-OFF-ELAPSED",
             "touched": "touched", "stale": "stale"}
    for path, _, sigs, infos in rows:
        head = sigs[0]
        tag = label.get(head["kind"], head["kind"])
        print(f"  • {path.stem:<42} {tag:<13} {head['evidence']}")
        for s in sigs[1:]:
            print(f"      └ {label.get(s['kind'], s['kind'])}: {s['evidence']}")
        for s in infos:
            print(f"      · {s['evidence']}")
    print("\nFlip a candidate (after confirming):")
    print("  ./.venv/bin/python tools/brief_sweep.py flip <brief.md> "
          "--to consumed|declined|superseded --note \"…\"" +
          (f" --sid8 {sid8}" if sid8 else ""))
    print("Default action is KEEP — do nothing and the brief stays open.")
    print("\n" + _backstop_coverage_line(n_open, n_missing))
    return 0


def _repo_root(start: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10).stdout.strip()
        return Path(out) if out else start
    except Exception:
        return start


def cmd_flip(args) -> int:
    path = Path(args.file)
    if not path.is_absolute():
        # accept bare name, handoff/brief/name, or full path
        cand = brief_dir() / Path(args.file).name
        path = cand if cand.is_file() else (Path.cwd() / args.file)
    if not path.is_file():
        print(f"flip: no such brief {args.file!r}", file=sys.stderr)
        return 2

    text = path.read_text()
    fm = parse_frontmatter(text)
    if not fm:
        print(f"flip: {path.name} has no frontmatter fence", file=sys.stderr)
        return 2
    old = fm.get("status", "open")
    if old == args.to:
        print(f"flip: {path.name} already {args.to} — no-op")
        return 0

    # edit only the status: line inside the first fence
    lines = text.splitlines(keepends=True)
    fence = [i for i, ln in enumerate(lines) if ln.strip() == "---"]
    if len(fence) < 2:
        print(f"flip: {path.name} malformed fence", file=sys.stderr)
        return 2
    lo, hi = fence[0], fence[1]
    changed = False
    for i in range(lo + 1, hi):
        if lines[i].split(":", 1)[0].strip() == "status":
            lines[i] = f"status: {args.to}\n"
            changed = True
            break
    if not changed:  # no status line — insert one just after the opening fence
        lines.insert(lo + 1, f"status: {args.to}\n")

    today = _dt.date.today().isoformat()
    sid = f", sid8 {args.sid8}" if args.sid8 else ""
    note = f" {args.note}" if args.note else ""
    body_note = f"\n_Lifecycle ({today}{sid}): status {old} → {args.to}.{note}_\n"
    out = "".join(lines)
    if not out.endswith("\n"):
        out += "\n"
    out += body_note
    path.write_text(out)

    # parse-verify (cf. frontmatter-normalizer pin: confirm we didn't stub it)
    v = parse_frontmatter(path.read_text())
    if not v or v.get("status") != args.to:
        print(f"flip: WARNING — post-write verify failed on {path.name}", file=sys.stderr)
        return 1
    print(f"flipped {path.name}: {old} → {args.to}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief-lifecycle collector (surfacer + safe flip).")
    sub = ap.add_subparsers(dest="cmd")

    r = sub.add_parser("report", help="surface retirement candidates (read-only)")
    r.add_argument("--json", action="store_true")
    r.add_argument("--stale-days", type=int, default=STALE_DAYS)
    r.add_argument("--needs-backstop", action="store_true",
                   help="lint: list open briefs with no dated auto-decline backstop "
                        "(cls != time-expiry). Read-only; surfacer, not a gate.")

    f = sub.add_parser("flip", help="apply one confirmed lifecycle flip")
    f.add_argument("file")
    f.add_argument("--to", required=True,
                   choices=["consumed", "declined", "superseded", "open"])
    f.add_argument("--note", default="")
    f.add_argument("--sid8", default="")

    # subcommand is optional: bare `brief_sweep.py [--flags]` defaults to report.
    argv = sys.argv[1:]
    if not argv or argv[0] not in ("report", "flip", "-h", "--help"):
        argv = ["report", *argv]
    args = ap.parse_args(argv)
    if args.cmd == "flip":
        return cmd_flip(args)
    return cmd_report(args)


if __name__ == "__main__":
    raise SystemExit(main())
