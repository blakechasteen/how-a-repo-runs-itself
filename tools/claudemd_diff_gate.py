#!/usr/bin/env python3
"""claudemd_diff_gate.py — push-boundary form gate on CLAUDE.md amendments.

Blake-greenlit 2026-07-11 (sid8 bfae1d13) as a P0 sibling to
handoff/brief/ci_governance_gates.md. CLAUDE.md's amendment procedure routes
edits by change class — factual-fix applies directly (declared in the commit
message), structural routes through a claudemd_* proposal brief that Blake
ratifies. Until now that procedure was purely behavioral: nothing mechanical
noticed an undeclared edit. This gate makes the *declaration* mandatory at the
push boundary.

FORM, never content: a commit touching hololoom_mcp/CLAUDE.md passes iff its
message either
  (a) declares the factual tier — contains "factual-fix" (or "factual fix"), OR
  (b) cites its proposal — contains a claudemd_<slug> reference AND
      hololoom_mcp/handoff/brief/claudemd_<slug>.md exists at that commit.
      (WARN, not fail, when the cited brief's status isn't yet `consumed` at
      that commit — the ratify merge and the status flip may land adjacent.)
  (c) declares the live-direction route — contains "blake-directed" (or
      "Blake directed"). CLAUDE.md's own amendment procedure says a change
      Blake directs live in-session *is* the ratification, no brief/cooling-off
      cycle required on top of it — this is that route's declaration, added
      2026-07-13 after the gate itself caught a real instance of the gap
      (5d6fd48, the governance-gut commit that added the clause, had no
      accepted declaration for its own route: see
      handoff/brief/claudemd_amendment_legibility.md).

The gate never judges whether an edit is *really* factual, whether a proposal
*should* be ratified, or whether Blake actually directed a given change — that
stays with Blake (project_propose_dispose_tension). It forces the class
declaration, so a bypass is a visible, anchored act instead of a silent one
(detection-over-prevention, docs/ci_cd_claims_integration_map.md § trust
topology).

Grandfathering is inherent: only commits in the pushed range are checked;
history before the gate is never re-litigated.

`--tally` mode makes the amendment procedure's tripwire mechanical: "if
blake-directed is the only route seen in months, the second-opinion property
is gone — push back" (CLAUDE.md § amendment procedure) becomes a count you can
read instead of a vibe. Reuses the same git history the gate already walks —
no separate log file to keep in sync.

Gate retirement condition: review at the H2 identity landing (session_chain
unify) — once amendments carry chain-anchored attestations, this message-shape
check may be subsumed. A routed-around gate is dead; re-scope it before that.

Dependency-free, 3.9-compatible.

Usage:
    python3 tools/claudemd_diff_gate.py                       # origin/main..HEAD
    python3 tools/claudemd_diff_gate.py --range A..B          # explicit range
    python3 tools/claudemd_diff_gate.py --before SHA --head SHA   # CI (push event)
    python3 tools/claudemd_diff_gate.py --tally [--since DATE] [--range A..B]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # tools/ on path
import frontmatter  # noqa: E402 — the shared runtime reader

WATCH = "hololoom_mcp/CLAUDE.md"
BRIEF_AT = "hololoom_mcp/handoff/brief/%s.md"
ZEROS = "0" * 40

_FACTUAL = re.compile(r"factual[- ]fix", re.IGNORECASE)
_CITE = re.compile(r"\bclaudemd_[a-z0-9_]+\b")
_BLAKE_DIRECTED = re.compile(r"blake[- ]directed", re.IGNORECASE)


def _git(args, cwd=None):
    """Run git, return (rc, stdout). Never raises on nonzero."""
    r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout


def _resolves(rev: str, cwd) -> bool:
    rc, _ = _git(["rev-parse", "--verify", "--quiet", rev + "^{commit}"], cwd)
    return rc == 0


def resolve_range(args, cwd) -> "tuple[str, str]":
    """Return (range_spec, honesty_note). Falls back to HEAD-only — with a
    printed note, never silently (no silent caps)."""
    if args.range:
        return args.range, ""
    if args.head:
        head = args.head
        before = args.before or ""
        if before and before != ZEROS and _resolves(before, cwd):
            return "%s..%s" % (before, head), ""
        return head + " -1", (
            "note: push base unavailable (new ref or shallow clone) — "
            "gating HEAD only; earlier commits in this push are NOT checked")
    if _resolves("origin/main", cwd):
        return "origin/main..HEAD", ""
    return "HEAD -1", "note: origin/main unavailable — gating HEAD only"


def commits_touching(range_spec: str, cwd) -> "list[str]":
    argv = ["log", "--format=%H"] + range_spec.split() + ["--", WATCH]
    rc, out = _git(argv, cwd)
    if rc != 0:
        print("FATAL: git log failed for range '%s'" % range_spec)
        raise SystemExit(2)
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def brief_status_at(sha: str, slug: str, cwd) -> "str | None":
    """The cited brief's `status` at that commit, or None if absent there."""
    rc, blob = _git(["show", "%s:%s" % (sha, BRIEF_AT % slug)], cwd)
    if rc != 0:
        return None
    fm = frontmatter.parse_frontmatter(blob, lowercase_keys=True)
    if not fm:
        return ""
    return str(fm.get("status", "") or "").strip().lower()


def classify_commit(sha: str, cwd) -> "tuple[str, bool, str]":
    """(cls, passes, detail) for one CLAUDE.md-touching commit.

    cls in {"factual-fix", "blake-directed", "brief-cite", "undeclared"} —
    the shared classification `check_commit` (gate) and `--tally` (tripwire
    count) both read, so the two never drift apart.
    """
    _, msg = _git(["log", "-1", "--format=%B", sha], cwd)
    if _FACTUAL.search(msg):
        return "factual-fix", True, "declares factual-fix"
    if _BLAKE_DIRECTED.search(msg):
        return "blake-directed", True, "declares blake-directed"
    cites = _CITE.findall(msg)
    for slug in cites:
        status = brief_status_at(sha, slug, cwd)
        if status is None:
            continue  # cited brief not present at this commit — keep looking
        detail = "cites %s" % slug
        if status != "consumed":
            detail += " (WARN: brief status '%s', not consumed, at this commit)" % status
        return "brief-cite", True, detail
    if cites:
        return "undeclared", False, ("cites %s but no such brief exists at this commit"
                       % ", ".join(sorted(set(cites))))
    return "undeclared", False, ("no change-class declaration (neither factual-fix, "
                                  "blake-directed, nor a claudemd_* citation)")


def check_commit(sha: str, cwd) -> "tuple[bool, str]":
    """(passes, detail) for one CLAUDE.md-touching commit."""
    _cls, ok, detail = classify_commit(sha, cwd)
    return ok, detail


def run_tally(args, cwd) -> int:
    """--tally: classify every CLAUDE.md-touching commit in range — the
    mechanical read for the amendment procedure's second tripwire ("if
    blake-directed is the only route seen in months, push back")."""
    range_spec = args.range or "HEAD"
    argv = ["log", "--format=%H"]
    if args.since:
        argv += ["--since", args.since]
    argv += range_spec.split() + ["--", WATCH]
    rc, out = _git(argv, cwd)
    if rc != 0:
        print("FATAL: git log failed for range '%s'" % range_spec)
        return 2
    shas = [ln.strip() for ln in out.splitlines() if ln.strip()]

    since_note = (" since %s" % args.since) if args.since else ""
    if not shas:
        print("claudemd-diff-gate --tally: no commits touching %s in %s%s"
              % (WATCH, range_spec, since_note))
        return 0

    counts = {"factual-fix": 0, "blake-directed": 0, "brief-cite": 0, "undeclared": 0}
    for sha in shas:
        cls, _ok, detail = classify_commit(sha, cwd)
        counts[cls] += 1
        print("  %-14s %s  %s" % (cls, sha[:10], detail))

    total = len(shas)
    print("claudemd-diff-gate --tally: %d commit(s) touching %s in %s%s"
          % (total, WATCH, range_spec, since_note))
    for cls in ("factual-fix", "blake-directed", "brief-cite", "undeclared"):
        n = counts[cls]
        pct = (100.0 * n / total) if total else 0.0
        print("  %-14s %3d  (%.0f%%)" % (cls, n, pct))
    if counts["blake-directed"] == total and total > 1:
        print("=> TRIPWIRE: every declared commit in this window is "
              "blake-directed — the second-opinion property may be gone. "
              "Push back (CLAUDE.md § amendment procedure).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--range", help="explicit git range, e.g. origin/main..HEAD")
    ap.add_argument("--before", help="push-event base SHA (may be all zeros)")
    ap.add_argument("--head", help="push-event head SHA")
    ap.add_argument("--tally", action="store_true",
                     help="classify every CLAUDE.md commit in range instead of gating")
    ap.add_argument("--since", help="tally only: git-log --since date filter, e.g. '90 days ago'")
    args = ap.parse_args()
    cwd = None  # current directory; gate paths are repo-root-relative
    rc, top = _git(["rev-parse", "--show-toplevel"])
    if rc != 0:
        print("FATAL: not inside a git repository")
        return 2
    cwd = top.strip()

    if args.tally:
        return run_tally(args, cwd)

    range_spec, note = resolve_range(args, cwd)
    if note:
        print("  " + note)

    shas = commits_touching(range_spec, cwd)
    if not shas:
        print("claudemd-diff-gate: no commits touching %s in %s — OK"
              % (WATCH, range_spec))
        return 0

    n_fail = 0
    for sha in shas:
        ok, detail = check_commit(sha, cwd)
        tag = "ok  " if ok else "FAIL"
        print("  %s  %s  %s" % (tag, sha[:10], detail))
        if not ok:
            n_fail += 1

    print("claudemd-diff-gate: %d CLAUDE.md commit(s) in %s, %d undeclared"
          % (len(shas), range_spec, n_fail))
    if n_fail:
        print("=> GATE FAILED — CLAUDE.md edits must declare their change class "
              "(CLAUDE.md § amendment procedure): say 'factual-fix' in the commit "
              "message, cite the ratified claudemd_<slug> proposal brief, or say "
              "'blake-directed' for the live-direction route. Form only: this "
              "gate never judges the edit itself.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
