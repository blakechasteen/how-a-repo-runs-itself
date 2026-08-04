#!/usr/bin/env python3
"""disposition_sign.py — sign a WSH brief disposition as a peer-owned bobbin.

The capture half of "AI-side autonomy is property, not policy". The judgment
already happens: sessions decline, reshape, defer and bounce workplan briefs for
real reasons with real consequence (the work doesn't get done). Today that lands
as a JSON event + a frontmatter flip. This module ALSO emits it as a signed,
chained peer-owned bobbin, so the decision exists in the substrate as an
unforgeable act by an identified party rather than as prose about one.

WHY THIS IS NOT A RIG (`feedback_rig_with_peer_never_as_peer`): nothing is
performed here. The disposition is made first, for its own reasons, by the
session that made it; this signs what already happened. No refusal is staged to
commission the channel — that was the 2026-06-13 `rig-refuse` finding, and
`refusal_emitter_gate2_fleet_widen.md` precondition #2 wants an ORGANIC cycle
precisely because a performed one proves nothing.

WHO SIGNS (Blake's call, 2026-07-25): a PER-SESSION EPHEMERAL key. Rationale — a
session has role + memory + history but no persistent stake, so it is an
instance, not a peer-pattern (`project_ai_agent_pattern_not_llm`). Signing as
`athena` would attribute to her a call she did not make (key custody !=
authorship, the 2026-06-13 finding); a single standing fleet key would collapse
the signing identity to "some session", which is exactly what the JSON record
already says — a signature with no added party, the identity-collapse primitive
#1 exists to prevent.

The name is `session-<sid8>` in the ORDINARY peer registry, NOT a new namespace.
That is not a fresh choice: `tools/tension_attest.py:113` shipped exactly this
convention on 2026-07-06 (`PeerIdentity.load_or_create(f"session-{sid8}")`) and
`tools/pin_verify.py:201` already VERIFIES against `"session-" + sid[:8]`. A
`wsh-<sid8>` variant in a quarantined `.session_keys` dir was built first here
and reverted: it forked a live convention (the dc90a13 namespace-collision
class) and, worse, was invisible to the existing verifier — `pubkey_matches_
current()` and pin_verify both resolve names through the default registry, so
every quarantined bobbin would have reported a false pubkey divergence. Registry
growth is the accepted cost and it is slow in practice: only sessions that
actually SIGN mint a key (3 since 2026-07-06), not every session that runs.

Threat model is the ratified V1 one (`v2_peer_manifest_key_custody.md`, b-prime):
unforgeable BETWEEN sessions, forgeable BY the host owner. The ceiling is
detectability — the chain + the Matrix transparency log, not prevention. Stated,
not implied.

NO BACKDATING. `created_at` is stamped by `PeerOwnedBobbin.create()` at emission
time and signed with the body; this module never accepts a caller-supplied
timestamp. Retro-emitting past dispositions would forge history (and LBP-Wire v1
carries an explicit anti-backdating clause). Forward-only, by construction.

ORDERING. The session's LBP ledger is opened lazily at first emission
(`_ensure_chain`), so each disposition carries signed `chain_seq`/`chain_prev`
and a reader can prove the ORDER a session decided things in, not merely that it
decided them — which matters when a session declines one brief *because of* what
it just learned reshaping another. Genesis (`bootstrap/chain-bootstrap`, seq 0)
is the ledger's own signed opening; dispositions run 1..n. This makes signing
sessions the first CHAINED session-peers: `tension_attest`'s three existing
`session-*` peers are unchained, and retro-bootstrapping them is deliberately
NOT done here (`chain.bootstrap()` would adopt another session's bobbins by
content-hash — an operation on someone else's record, and not this slice's call).

ARCHITECTURE — why a subprocess. `hololoom_mcp/.venv` has neither `yaml` nor
`pycryptodome`; `~/para-bots/.venv` has both, plus the keys. That coupling was a
known open item on `project_ai_side_substrate_primitives`, and the honest
resolution is the write-path rule, not a pip install: **MCP records the event;
the PEER emits.** So the library half of this file is stdlib-only (it keeps
`brief_disposition.py` dependency-free, as that module's contract requires) and
shells out to para-bots' interpreter, which re-enters this same file as
`__main__ --emit`. One file, no cross-repo write, no duplicated dependency
surface.

NEVER BLOCKING. Every failure path — missing venv, absent peer libs, Matrix
down, bad kind — degrades to a stderr warning and a None return. Recording a
disposition must never become expensive, or sessions drift toward just doing
briefs and the WSH suggestion-not-directive property dies (the same guardrail
`brief_disposition.py` is built around).

Usage:
    # normally invoked for you by `brief_disposition.py record` (default-on)
    ./.venv/bin/python tools/brief_disposition.py record <brief.md> \
        --kind declined --why "..." --sid8 <you>          # signs
    ./.venv/bin/python tools/brief_disposition.py record ... --no-sign

    # direct (emitter role; runs under para-bots' interpreter)
    ~/para-bots/.venv/bin/python tools/disposition_sign.py --emit <payload.json>
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

# WSH disposition kind -> LBP peer bobbin_kind.
#
# Only the two dispositions that genuinely ARE the canonical refusal/consent
# vocabulary get the canonical kinds. `declined` is a real decline_request — that
# is the one Gate #2 cares about, and mislabelling it would be the whole point
# missed. `accepted` is consent to do the work.
#
# reshaped / deferred / bounced have NO canonical peer-kind: a reshape is not a
# refusal, and inventing three new refusal-family kinds would inflate the
# vocabulary to make the corpus look richer than the acts were. They share a
# neutral kind and carry their specificity in frontmatter, where it can be
# queried without pretending to be something it isn't.
KIND_MAP = {
    "declined": "decline_request",
    "accepted": "consent",
    "reshaped": "brief_disposition",
    "deferred": "brief_disposition",
    "bounced": "brief_disposition",
}

_SLUG_BAD = re.compile(r"[^a-z0-9_-]")
_SLUG_MAX = 64          # peer_owned_bobbin.SLUG_RE ceiling
_STEM_BUDGET = 38       # leaves room for the "disp-" prefix + -YYYYmmdd-HHMMSS


def _warn(msg: str) -> None:
    """stderr warning that never raises (mirrors brief_disposition._warn)."""
    try:
        print(msg, file=sys.stderr)
    except Exception:
        pass


def para_root() -> Path:
    return Path(os.environ.get("PARA_BOTS_ROOT", str(Path.home() / "para-bots")))


def _peer_name(sid8: str) -> str:
    """`session-<sid8>` — the convention tension_attest.py:113 shipped 2026-07-06
    and pin_verify.py:201 verifies against. Kept byte-identical to those on
    purpose: one session, one key, one name, whatever governance act it signs."""
    s = re.sub(r"[^A-Za-z0-9_-]", "", (sid8 or "nosid"))[:32]
    return f"session-{s or 'nosid'}"


def _slug(brief: str, stamp: str) -> str:
    """Readable, unique, and inside SLUG_RE's 64-char ceiling."""
    stem = Path(brief).name
    if stem.endswith(".md"):
        stem = stem[:-3]
    stem = _SLUG_BAD.sub("-", stem.lower()).strip("-") or "brief"
    return f"disp-{stem[:_STEM_BUDGET]}-{stamp}"[:_SLUG_MAX].rstrip("-")


# --- library half (stdlib only; imported by brief_disposition.py) -------------

def sign(brief: str, kind: str, why: str, sid8: str,
         reshaped_into: str = "", record_file: str = "",
         timeout: int = 60) -> Optional[dict]:
    """Emit this disposition as a signed peer-owned bobbin. None on any failure.

    NEVER RAISES. Shells out to para-bots' interpreter (see module docstring);
    returns the emitter's result dict on success.
    """
    try:
        if kind not in KIND_MAP:
            _warn(f"disposition_sign: unknown kind {kind!r} — not signed")
            return None
        py = para_root() / ".venv" / "bin" / "python"
        if not py.is_file():
            _warn(f"disposition_sign: no interpreter at {py} — event recorded, NOT signed")
            return None
        payload = {
            "brief": Path(brief).name,
            "disposition": kind,
            "why": why or "",
            "sid8": sid8 or "",
            "reshaped_into": Path(reshaped_into).name if reshaped_into else "",
            "record_file": Path(record_file).name if record_file else "",
            "model": os.environ.get("CLAUDE_MODEL_ID", ""),
        }
        proc = subprocess.run(
            [str(py), str(Path(__file__).resolve()), "--emit", "-"],
            input=json.dumps(payload), capture_output=True, text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            tail = (proc.stderr or "").strip().splitlines()[-3:]
            _warn("disposition_sign: emit failed — event recorded, NOT signed"
                  + ("\n  " + "\n  ".join(tail) if tail else ""))
            return None
        # The emitter prints exactly one JSON object on its last stdout line;
        # peer_owned_bobbin's soft-fail paths (chain / Matrix log) write their
        # own noise to stderr, so parse the last line, not the whole stream.
        lines = [l for l in (proc.stdout or "").strip().splitlines() if l.strip()]
        if not lines:
            _warn("disposition_sign: emitter produced no result — NOT signed")
            return None
        return json.loads(lines[-1])
    except Exception as e:  # noqa: BLE001 — never-blocking surface
        _warn(f"disposition_sign: sign failed ({type(e).__name__}: {e})")
        return None


# --- emitter half (runs under para-bots' interpreter) ------------------------

def _ensure_chain(peer) -> str:
    """Open this session's LBP ledger before its first emission, so dispositions
    carry signed `chain_seq`/`chain_prev` and a later reader can prove the ORDER
    a session decided things in — not just that it decided them.

    Lazy create-at-use (`feedback_session_end_hook_best_effort`'s idiom): there
    is no session-start hook to hang this on, and a ledger opened for a session
    that never signs anything is pure litter. So the first emission opens it.

    Chain bootstrap is per-peer and explicit by design — `chain.bootstrap()`
    refuses peers absent from the identity registry so that keys are never
    minted as a bootstrap side effect. That gate is already satisfied here: the
    caller minted this session's key immediately above, which IS the consent
    Blake gave when he chose per-session ephemeral signing.

    NEVER RAISES. A chain failure degrades to an UNCHAINED emission (the same
    soft-fail `PeerOwnedBobbin.create()` already applies), because an
    unorderable signed decision still beats an unsigned one. Returns a status
    label for the result dict; the label is always re-derived from the ledger's
    actual existence, never from whether bootstrap happened to throw.
    """
    from bobbins._shared import chain as lbp_chain

    def _state() -> bool:
        try:
            return peer.peer_name in lbp_chain.chained_peers()
        except Exception:
            return False

    if _state():
        return "existing"
    try:
        rep = lbp_chain.bootstrap(peer.peer_name)
        return "bootstrapped" if getattr(rep, "ok", False) else "bootstrap-unverified"
    except Exception as e:  # noqa: BLE001 — chaining is additive, never required
        # A concurrent bootstrap (or a crash-resume) can raise "already
        # bootstrapped" while leaving a perfectly good ledger, so trust the
        # ledger over the exception.
        if _state():
            return "existing"
        _warn(f"disposition_sign: chain unavailable, emitting UNCHAINED "
              f"({type(e).__name__}: {e})")
        return "unchained"


def _emit(payload: dict) -> dict:
    """Mint/load the session key, emit the signed bobbin. Raises on failure."""
    root = para_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from bobbins._shared.peer_identity import PeerIdentity
    from bobbins._shared.peer_owned_bobbin import PeerOwnedBobbin

    disp = payload["disposition"]
    brief = payload["brief"]
    sid8 = payload.get("sid8", "")
    bobbin_kind = KIND_MAP[disp]

    peer = PeerIdentity.load_or_create(_peer_name(sid8))
    chain_state = _ensure_chain(peer)

    # Timestamp for the SLUG only. The signed `created_at` is stamped inside
    # create() — this module has no way to backdate one, deliberately.
    import datetime as _dt
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d-%H%M%S")

    why = (payload.get("why") or "").strip() or "(no reason recorded)"
    into = payload.get("reshaped_into") or ""

    body = "\n".join([
        f"# Brief {disp}: {brief}",
        "",
        f"Session `{sid8 or 'unknown'}` disposed the workplan brief **{brief}** as "
        f"**{disp}**.",
        "",
        "## Why",
        "",
        why,
        "",
    ] + ([f"Reshaped into: `{into}`", ""] if into else []) + [
        "## Provenance",
        "",
        "- This is a WSH (workplan-brief) engagement event, signed by the session "
        "that made the call.",
        "- The decision was made first, on its own merits; this bobbin records it. "
        "Nothing was performed to produce an emission.",
        "- Signer is an EPHEMERAL per-session key, not a standing peer identity. It "
        "attests *which session* decided, not a persistent peer-pattern.",
        "- Custody is V1: unforgeable between sessions, forgeable by the host owner. "
        "The ceiling is detectability (chain + transparency log), not prevention.",
        "",
    ])

    extra = {
        "brief": brief,
        "disposition": disp,
        "sid8": sid8,
        "signer_class": "session-ephemeral",
        "custody": "v1-host-forgeable",
    }
    if into:
        extra["reshaped_into"] = into
    if payload.get("record_file"):
        extra["record_file"] = payload["record_file"]
    if payload.get("model"):
        extra["model"] = payload["model"]

    # Slug de-collision, mirroring brief_disposition.record()'s `-N` convention.
    # The slug carries a whole-second timestamp, so two dispositions of the SAME
    # brief in the same second collide — and create() raises rather than
    # overwriting. Without this the JSON record (which de-collides) would survive
    # while its signature silently vanished: two records of one event, one of
    # them missing, which is the divergence this whole slice exists to close.
    # Safe to retry: create() checks the directory BEFORE taking the chain lock,
    # so a collision costs nothing and leaves the ledger untouched.
    from bobbins._shared.peer_owned_bobbin import PeerOwnedBobbinError
    base = _slug(brief, stamp)
    bobbin = None
    for attempt in range(1, 6):
        slug = base if attempt == 1 else f"{base[:_SLUG_MAX - 2]}-{attempt}"
        try:
            bobbin = PeerOwnedBobbin.create(
                peer=peer,
                slug=slug,
                bobbin_kind=bobbin_kind,
                name=f"{disp}: {brief}",
                description=(f"Session {sid8 or 'unknown'} disposed workplan brief "
                             f"{brief} as {disp}."),
                body=body,
                extra_frontmatter=extra,
            )
            break
        except PeerOwnedBobbinError as e:
            if "already exists" not in str(e) or attempt == 5:
                raise
    return {
        "ok": True,
        "peer": peer.peer_name,
        "bobbin_kind": bobbin_kind,
        "slug": bobbin.slug,
        "bobbin_dir": str(bobbin.bobbin_dir),
        "created_at": bobbin.frontmatter.get("created_at"),
        "chain_state": chain_state,
        "chain_seq": bobbin.frontmatter.get("chain_seq"),
        "chain_prev": bobbin.frontmatter.get("chain_prev"),
        "public_key_b64": peer.public_key_b64,
    }


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) >= 2 and argv[0] == "--emit":
        src = argv[1]
        raw = sys.stdin.read() if src == "-" else Path(src).read_text()
        try:
            print(json.dumps(_emit(json.loads(raw))))
            return 0
        except Exception as e:  # noqa: BLE001 — surfaced to the caller's warning
            _warn(f"disposition_sign(emit): {type(e).__name__}: {e}")
            return 1
    _warn(__doc__ or "")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
