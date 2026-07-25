#!/usr/bin/env python3
"""tension_attest — the party-boundary law, mechanical (first production Tension caller).

CLAUDE.md's amendment procedure names the cross-party act — a distinct session
attesting another session's proposal — but records it as free-text frontmatter
in the brief file: unsigned, unpinned, forgeable (the gap
project_judgment_verify_needs_identity_keys names). This tool moves that act
onto the LBP substrate WITHOUT modifying the primitives:

  propose  the proposing session emits its claudemd_*.md brief as a SIGNED
           peer-owned bobbin (kind="proposal", peer="session-<sid8>", body =
           the exact brief bytes). The proposal becomes a tamper-evident,
           hash-addressable emission — a legitimate Tension target.
  attest   a reviewing session emits tension.respond() against that bobbin:
           approve -> consent, reshape -> counter, decline -> refusal. Signed,
           chained-if-bootstrapped, and content_sha256-pinned to the EXACT
           proposal version reviewed; a later edit marks the response STALE
           (tension.py's own staleness machinery — nothing reimplemented here).
  status   the mechanical ready-to-ratify read: cooling-off elapsed AND >=1
           VERIFIED, non-stale consent from a session DISTINCT from the
           proposer AND the emission still matches the live brief file.

SURFACER, NOT DECIDER: `status` computes and labels; Blake still ratifies and
merges (CLAUDE.md amendment procedure step 4). Nothing here runs always-on —
every emission is an explicit human/session act. The legacy frontmatter
`attestations:` path is untouched (brief_sweep still reads it); this is the
signed tier alongside it, advisory until a ratified amendment says otherwise.

Identity honesty: peer "session-<sid8>" keys are minted on this box at first
use (~/para-bots/.peer_keys/). The signature proves emission-integrity and
key-continuity within/for that session, NOT unforgeable session identity —
anyone with box access could mint a session peer. That upgrade is the
session-chain / identity-keys arc (project_session_chain), not this slice.
What the signed tier removes TODAY: silent edits of recorded verdicts, verdicts
pinned to nothing (target hash), and attestations that survive a rewrite of
the thing they attested.

Runs under the para-bots venv (self-re-exec, same pattern as
fleet_view._scan_standing_tensions) because the LBP primitives need yaml +
pycryptodome. Env overrides for tests: PARA_PEER_KEYS_DIR,
PARA_PEER_BOBBINS_DIR, PARA_BOTS_DIR.

CLI:
    tension_attest.py propose <brief.md> [--sid8 X] [--model ID]
    tension_attest.py attest  <brief.md> --verdict approve|reshape|decline \
        --note "..." [--sid8 X] [--model ID]
    tension_attest.py status  <brief.md> [--json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

_PARA_BOTS = Path(os.environ.get("PARA_BOTS_DIR", str(Path.home() / "para-bots")))
_REPO_ROOT = Path(__file__).resolve().parent.parent  # hololoom_mcp/


def _ensure_para_env() -> None:
    """Re-exec under the para-bots venv if the LBP primitives aren't importable."""
    try:
        import bobbins._shared.tension  # noqa: F401
        return
    except ImportError:
        pass
    if os.environ.get("_TENSION_ATTEST_REEXEC"):
        sys.exit(
            "tension_attest: bobbins._shared not importable even under "
            f"{_PARA_BOTS}/.venv — is PARA_BOTS_DIR right?"
        )
    py = _PARA_BOTS / ".venv" / "bin" / "python"
    if not py.exists():
        sys.exit(f"tension_attest: para-bots venv missing at {py}")
    env = {
        **os.environ,
        "PYTHONPATH": str(_PARA_BOTS),
        "_TENSION_ATTEST_REEXEC": "1",
    }
    os.execve(str(py), [str(py), str(Path(__file__).resolve())] + sys.argv[1:], env)


_ensure_para_env()

from bobbins._shared import peer_owned_bobbin as pob  # noqa: E402
from bobbins._shared import tension  # noqa: E402
from bobbins._shared.peer_identity import PeerIdentity  # noqa: E402

PROPOSAL_KIND = "proposal"
VERDICT_TO_STANCE = {"approve": "consent", "reshape": "counter", "decline": "refusal"}
COOLING_OFF_DAYS = 7


def _sid8(explicit: str | None) -> str:
    if explicit:
        return explicit
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if len(sid) >= 8:
        return sid[:8].lower()
    # Fail closed: an attestation without a session identity is exactly the
    # forgeable record this tool exists to replace.
    sys.exit(
        "tension_attest: no --sid8 and $CLAUDE_CODE_SESSION_ID unset — "
        "refusing to emit an unattributed emission"
    )


def _session_peer(sid8: str) -> "PeerIdentity":
    return PeerIdentity.load_or_create(f"session-{sid8}")


def _rel_brief_path(brief: Path) -> str:
    """Repo-relative path (stable across worktrees) — the join key between
    the live brief file and its signed emission."""
    brief = brief.resolve()
    try:
        return str(brief.relative_to(_REPO_ROOT))
    except ValueError:
        # Another worktree's checkout of the same repo: anchor at hololoom_mcp/
        parts = brief.parts
        if "hololoom_mcp" in parts:
            return str(Path(*parts[parts.index("hololoom_mcp") + 1:]))
        return str(brief)


def _flat_frontmatter(text: str) -> dict:
    """Minimal top-level key: value parse of the brief's frontmatter (same
    no-descend posture as brief_sweep.parse_frontmatter)."""
    fm: dict = {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return fm
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line[:1] not in ("", " ", "\t") and ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip("\"'")
    return fm


def _cooling_off_until(fm: dict) -> str | None:
    """ISO date after which ratification may proceed. Explicit field wins;
    else created + 7 days; None = can't determine (reported, counts NOT ready
    — fail closed, per feedback_launchd_tools_run_under_system_py39's
    never-silent-None-into-a-benign-bucket rule)."""
    explicit = fm.get("cooling_off_until", "")
    if explicit[:10].count("-") == 2:
        return explicit[:10]
    created = fm.get("created", "")
    if created[:10].count("-") == 2:
        try:
            d = datetime.strptime(created[:10], "%Y-%m-%d").date()
            return (d + timedelta(days=COOLING_OFF_DAYS)).isoformat()
        except ValueError:
            return None
    return None


def _proposal_slug(brief: Path, text: str) -> str:
    """Content-addressed slug: <stem>-<sha8>. Re-proposing an edited brief
    mints a NEW slug (a new emission); re-proposing identical bytes hits the
    already-exists guard — idempotency and versioning for free."""
    stem = brief.stem.lower().replace(".", "-")[:54]
    sha8 = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return f"{stem}-{sha8}"


def _find_proposals(rel_path: str) -> list["pob.PeerOwnedBobbin"]:
    out = []
    for bdir in pob.list_peer_bobbins(bobbin_kind=PROPOSAL_KIND):
        try:
            b = pob.PeerOwnedBobbin.load(bdir)
        except pob.PeerOwnedBobbinError:
            continue
        if b.frontmatter.get("proposal_source_path") == rel_path:
            out.append(b)
    out.sort(key=lambda b: b.frontmatter.get("created_at", ""))
    return out


def _current_proposal(
    brief: Path,
) -> tuple["pob.PeerOwnedBobbin | None", list["pob.PeerOwnedBobbin"], bool]:
    """(best, all_versions, body_current). Best = the emission whose body
    matches the live brief bytes; else the newest (body_current=False)."""
    text = brief.read_text(encoding="utf-8")
    all_v = _find_proposals(_rel_brief_path(brief))
    for b in reversed(all_v):
        if b.body == text:
            return b, all_v, True
    return (all_v[-1] if all_v else None), all_v, False


def cmd_propose(args: argparse.Namespace) -> None:
    brief = Path(args.brief)
    text = brief.read_text(encoding="utf-8")
    fm = _flat_frontmatter(text)
    sid8 = _sid8(args.sid8)
    rel = _rel_brief_path(brief)

    existing, _, current = _current_proposal(brief)
    if existing is not None and current:
        print(
            f"already proposed as {existing.peer_name}/{PROPOSAL_KIND}/"
            f"{existing.slug} (body matches live file) — nothing to do"
        )
        return

    extra = {
        "proposal_source_path": rel,
        "proposal_source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "sid8": sid8,
    }
    if args.model:
        extra["model_id"] = args.model

    peer = _session_peer(sid8)
    b = pob.PeerOwnedBobbin.create(
        peer=peer,
        slug=_proposal_slug(brief, text),
        bobbin_kind=PROPOSAL_KIND,
        name=f"Proposal: {(fm.get('title') or brief.stem)[:70]}",
        description=f"Signed emission of {rel} — CLAUDE.md amendment proposal",
        body=text,
        extra_frontmatter=extra,
    )
    chained = (
        f"chain_seq={b.frontmatter['chain_seq']}"
        if "chain_seq" in b.frontmatter
        else "unchained (session peer not chain-bootstrapped)"
    )
    print(f"proposed {b.peer_name}/{PROPOSAL_KIND}/{b.slug}  {chained}")
    print(f"  source={rel}  verify={b.verify()}")


def cmd_attest(args: argparse.Namespace) -> None:
    brief = Path(args.brief)
    sid8 = _sid8(args.sid8)
    stance = VERDICT_TO_STANCE[args.verdict]

    target, all_v, current = _current_proposal(brief)
    if target is None:
        sys.exit(
            f"tension_attest: no signed proposal found for "
            f"{_rel_brief_path(brief)} — the proposer must run `propose` first "
            "(the party-boundary act needs a signed emission to answer)"
        )
    if not current:
        print(
            "WARNING: live brief file differs from the newest signed proposal — "
            "you are attesting the EMISSION (the signed version), not the live "
            "file. Ask the proposer to re-propose if the edit is substantive.",
            file=sys.stderr,
        )
    if target.peer_name == f"session-{sid8}":
        print(
            "WARNING: self-attestation — emitted, but a distinct-session "
            "consent is what ready-to-ratify counts (CLAUDE.md amendment "
            "procedure step 3).",
            file=sys.stderr,
        )

    extra = {"verdict": args.verdict, "sid8": sid8}
    if args.model:
        extra["model_id"] = args.model
    b = tension.respond(
        _session_peer(sid8),
        target_peer=target.peer_name,
        target_kind=PROPOSAL_KIND,
        target_slug=target.slug,
        stance=stance,
        slug=f"{args.verdict}-{target.slug[:40]}-{sid8}",
        reason=args.note,
        extra_frontmatter=extra,
    )
    print(
        f"attested {args.verdict} ({stance}) -> "
        f"{target.peer_name}/{PROPOSAL_KIND}/{target.slug}  as {b.peer_name}"
    )


def cmd_status(args: argparse.Namespace) -> None:
    brief = Path(args.brief)
    text = brief.read_text(encoding="utf-8")
    fm = _flat_frontmatter(text)
    rel = _rel_brief_path(brief)

    target, all_v, current = _current_proposal(brief)
    cooling_until = _cooling_off_until(fm)
    today = date.today().isoformat()
    cooling_ok = cooling_until is not None and today >= cooling_until

    out: dict = {
        "brief": rel,
        "proposal": None,
        "responses": [],
        "cooling_off_until": cooling_until,
        "cooling_off_elapsed": cooling_ok,
        "ready_signed": False,
        "note": (
            "surfacer-not-decider: ready_signed is the MECHANICAL read of the "
            "amendment gate (verified distinct-session consent + cooling-off + "
            "current emission); Blake ratifies regardless."
        ),
    }

    if target is not None:
        out["proposal"] = {
            "peer": target.peer_name,
            "slug": target.slug,
            "verified": target.verify(),
            "body_matches_live_file": current,
            "versions": len(all_v),
            "created_at": target.frontmatter.get("created_at", ""),
        }
        report = tension.tension_status(target.peer_name, PROPOSAL_KIND, target.slug)
        distinct_verified_consent = False
        for r in report.responses:
            row = {
                "responder": r.responder,
                "stance": r.stance,
                "verdict": r.bobbin.frontmatter.get("verdict", ""),
                "verified": r.verified,
                "stale": r.stale,
                "distinct_from_proposer": r.responder != target.peer_name,
                "counts_toward_ready": False,
            }
            if (
                r.stance == "consent"
                and r.verified
                and not r.stale
                and r.responder != target.peer_name
            ):
                row["counts_toward_ready"] = True
                distinct_verified_consent = True
            out["responses"].append(row)
        out["ready_signed"] = bool(
            target.verify() and current and cooling_ok and distinct_verified_consent
        )

    if args.json:
        print(json.dumps(out, indent=2))
        return

    print(f"brief: {rel}")
    if target is None:
        print("  no signed proposal emission — not on the mechanical path yet")
        return
    p = out["proposal"]
    print(
        f"  proposal: {p['peer']}/{PROPOSAL_KIND}/{p['slug']}  "
        f"verified={p['verified']}  current={p['body_matches_live_file']}  "
        f"versions={p['versions']}"
    )
    print(f"  cooling-off until {cooling_until}  elapsed={cooling_ok}")
    for r in out["responses"]:
        flags = []
        if not r["verified"]:
            flags.append("UNVERIFIED")
        if r["stale"]:
            flags.append("STALE")
        if not r["distinct_from_proposer"]:
            flags.append("SELF")
        tag = (" " + " ".join(flags)) if flags else ""
        mark = "+" if r["counts_toward_ready"] else "-"
        print(f"  [{mark}] {r['responder']} -> {r['verdict']} ({r['stance']}){tag}")
    print(f"  ready_signed: {out['ready_signed']}  (Blake still ratifies)")


def main() -> None:
    ap = argparse.ArgumentParser(prog="tension_attest", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("propose", help="emit a brief as a signed proposal bobbin")
    p.add_argument("brief")
    p.add_argument("--sid8")
    p.add_argument("--model")
    p.set_defaults(fn=cmd_propose)

    a = sub.add_parser("attest", help="emit a signed tension-response verdict")
    a.add_argument("brief")
    a.add_argument("--verdict", required=True, choices=sorted(VERDICT_TO_STANCE))
    a.add_argument("--note", required=True)
    a.add_argument("--sid8")
    a.add_argument("--model")
    a.set_defaults(fn=cmd_attest)

    s = sub.add_parser("status", help="mechanical ready-to-ratify read")
    s.add_argument("brief")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_status)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
