#!/usr/bin/env python3
"""
coord — Redis-backed cross-session coordination primitive (writer + lib).

Slice 1: PRESENCE. *Which Claude sessions are live right now, and where.*

This is the WRITE side of the hybrid coordination layer (the 2026-06-05
"leverage Redis" design). The MCP server (server.py) exposes the READ side
(hololoom_presence) over the same keys — keeping the server read-only *by
design* while writes flow through this CLI, invoked by session hooks
(SessionStart register / Stop heartbeat) and by Claude directly. Same split
as tools/index_*.py (writers) vs server.py (reader).

Transport: shells out to `docker exec <container> redis-cli` — NO redis-py
dependency added to the shared venv that the live MCP server + indexers run
from (mirrors data/olivetin/config.yaml's existing pattern). Swap _cli() for
redis-py only if a remote/non-docker Redis is ever needed.

Key schema (slice 1):
    presence:<sid8>  ->  JSON {sid8, cwd, worktree, branch, started_at,
                               last_seen, host, pid}   EX <ttl>

TTL is the design, not an afterthought. SessionEnd hooks are best-effort —
they "may not run" if Claude Code is killed (see the 240-orphaned-keys
incident, feedback_session_end_hook_best_effort). So "live" == "key hasn't
expired yet." No key => not live. The Stop hook (fires each turn boundary)
refreshes the TTL; a crashed session simply ages out. Lazy-create + TTL-expiry,
no must-run cleanup.

Designed to grow: `lock` (slice 1b) and `rl`/cooling-off (slice 2, C) hang
off the same _cli() transport and argparse tree.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

# ── config ──────────────────────────────────────────────────────────────────
REDIS_CONTAINER = os.environ.get("REDIS_CONTAINER", "redis")
DEFAULT_PRESENCE_TTL = int(os.environ.get("COORD_PRESENCE_TTL", "900"))    # 15 min
DEFAULT_LOCK_TTL = int(os.environ.get("COORD_LOCK_TTL", "1800"))          # 30 min
PRESENCE_PREFIX = "presence:"
LOCK_PREFIX = "lock:"


class CoordError(RuntimeError):
    """Redis transport / command failure."""


# ── transport ───────────────────────────────────────────────────────────────
def _cli(*args: str, timeout: float = 5.0) -> str:
    """Run `docker exec <container> redis-cli <args>` and return stripped stdout.

    Raises CoordError on any failure (docker missing, container down, redis
    error). Callers that must never break a session (hooks) catch this and
    degrade to a no-op.
    """
    cmd = ["docker", "exec", REDIS_CONTAINER, "redis-cli", *args]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError as e:
        raise CoordError(f"docker not found: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise CoordError(f"redis-cli timed out after {timeout}s") from e
    if proc.returncode != 0:
        raise CoordError(
            f"redis-cli exited {proc.returncode}: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout.strip()


# ── environment auto-detection (CLI convenience) ────────────────────────────
def _detect_cwd() -> str:
    return os.environ.get("COORD_CWD") or os.getcwd()


def _detect_branch(cwd: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3.0,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def _detect_worktree(cwd: str) -> str:
    """Worktree name if under .claude/worktrees/<name>/..., else 'main'."""
    parts = Path(cwd).resolve().parts
    if ".claude" in parts:
        i = parts.index(".claude")
        if i + 2 < len(parts) and parts[i + 1] == "worktrees":
            return parts[i + 2]
    return "main"


def _read_hook_stdin() -> dict:
    """Claude Code hooks deliver a JSON event on stdin (session_id, cwd, ...)."""
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def _sid8(value: str) -> str:
    """Normalize a session id (full UUID or already-8) to its 8-char handle."""
    v = (value or "").strip()
    return v[:8]


# ── presence: write ─────────────────────────────────────────────────────────
def register(
    sid8: str,
    *,
    cwd: str | None = None,
    worktree: str | None = None,
    branch: str | None = None,
    ttl: int = DEFAULT_PRESENCE_TTL,
    started_at: float | None = None,
) -> dict:
    """Create/refresh this session's presence key with a TTL."""
    cwd = cwd or _detect_cwd()
    now = time.time()
    rec = {
        "sid8": sid8,
        "cwd": cwd,
        "worktree": worktree if worktree is not None else _detect_worktree(cwd),
        "branch": branch if branch is not None else _detect_branch(cwd),
        "started_at": started_at if started_at is not None else now,
        "last_seen": now,
        "host": socket.gethostname(),
        "pid": os.getpid(),
    }
    _cli("SET", f"{PRESENCE_PREFIX}{sid8}", json.dumps(rec), "EX", str(ttl))
    return rec


def heartbeat(sid8: str, *, ttl: int = DEFAULT_PRESENCE_TTL) -> dict:
    """Refresh last_seen + TTL. Lazily registers if the key has aged out."""
    existing = _cli("GET", f"{PRESENCE_PREFIX}{sid8}")
    if not existing:
        # Aged out (or never registered) — recreate from current environment.
        return register(sid8, ttl=ttl)
    try:
        rec = json.loads(existing)
    except Exception:
        return register(sid8, ttl=ttl)
    rec["last_seen"] = time.time()
    _cli("SET", f"{PRESENCE_PREFIX}{sid8}", json.dumps(rec), "EX", str(ttl))
    return rec


def release(sid8: str) -> bool:
    """Remove this session's presence key (graceful exit). Idempotent."""
    out = _cli("DEL", f"{PRESENCE_PREFIX}{sid8}")
    return out.strip() == "1"


# ── presence: read (shared with the MCP read tool) ──────────────────────────
def list_presence() -> list[dict]:
    """All live sessions, newest-heartbeat first. Each record gains
    `ttl_remaining` (s) and `age` (s since last_seen). Never raises on a
    single malformed key; skips it."""
    keys_raw = _cli("--scan", "--pattern", f"{PRESENCE_PREFIX}*")
    keys = [k for k in keys_raw.splitlines() if k.strip()]
    if not keys:
        return []
    out: list[dict] = []
    now = time.time()
    for key in keys:
        val = _cli("GET", key)
        if not val:
            continue  # expired between scan and get
        try:
            rec = json.loads(val)
        except Exception:
            continue
        ttl = _cli("TTL", key)
        try:
            rec["ttl_remaining"] = int(ttl)
        except Exception:
            rec["ttl_remaining"] = None
        rec["age"] = round(now - rec.get("last_seen", now), 1)
        out.append(rec)
    out.sort(key=lambda r: r.get("last_seen", 0), reverse=True)
    return out


def _fmt_age(sec: float) -> str:
    sec = int(sec)
    if sec < 90:
        return f"{sec}s"
    if sec < 5400:
        return f"{sec // 60}m"
    return f"{sec // 3600}h"


def session_start(sid8: str, *, ttl: int = DEFAULT_PRESENCE_TTL) -> str | None:
    """Register this session, then build a heads-up of OTHER live sessions +
    locks held by others. Returns the heads-up text, or None when this session
    is alone (so a solo session adds zero noise). This is the SessionStart
    consumer — the bit that turns presence/locks from queryable into a nudge."""
    register(sid8, ttl=ttl)
    others = [s for s in list_presence() if s.get("sid8") != sid8]
    locks = [l for l in list_locks() if l.get("sid8") != sid8]
    if not others and not locks:
        return None

    lines: list[str] = []
    if others:
        lines.append(f"⚠ {len(others)} other Claude session(s) live on this host:")
        for s in others:
            wt = s.get("worktree") or "?"
            br = s.get("branch") or "-"
            lines.append(f"  • {s.get('sid8')}  wt={wt}  branch={br}  (seen {_fmt_age(s.get('age', 0))} ago)")
    if locks:
        lines.append(f"🔒 {len(locks)} file/resource(s) claimed by others:")
        for l in locks:
            res = l.get("resource", "?")
            short = res.split("/")[-1] if "/" in res else res
            lines.append(f"  • {l.get('sid8')} holds {short}   ({res})")
    lines.append(
        "→ Before editing a shared file, check `hololoom_locks` and claim it: "
        "`coord.py lock claim <path> --sid8 <you>`. See `hololoom_presence` for who's live."
    )
    return "\n".join(lines)


# ── locks: advisory claims on a resource (file / worktree / arbitrary key) ──
# Advisory, not enforced: Claude checks before editing. The atomic SET NX makes
# the claim race-safe across parallel sessions; TTL means a dead session's lock
# ages out instead of wedging the resource forever. Re-claim by the same holder
# refreshes (re-entrant); release is owner-checked.
def _lock_key(resource: str) -> str:
    h = hashlib.sha1(resource.encode("utf-8")).hexdigest()[:16]
    return f"{LOCK_PREFIX}{h}"


def _normalize_resource(resource: str) -> str:
    """Resolve to an absolute path if it looks like a filesystem path, so the
    same file claimed from different cwds collides on one key. Non-path
    resources (e.g. 'worktree:redis-coord') pass through verbatim."""
    r = resource.strip()
    if r.startswith(("/", "./", "../")) or os.sep in r and ":" not in r.split(os.sep)[0]:
        try:
            return str(Path(r).resolve())
        except Exception:
            return r
    return r


def claim_lock(
    resource: str,
    sid8: str,
    *,
    worktree: str | None = None,
    branch: str | None = None,
    ttl: int = DEFAULT_LOCK_TTL,
    force: bool = False,
) -> dict:
    """Atomically claim a resource. Returns {ok, resource, ...}. If already held
    by another session, ok=False + held_by (unless force). Same-holder re-claim
    refreshes the TTL (re-entrant)."""
    resource = _normalize_resource(resource)
    key = _lock_key(resource)
    cwd = _detect_cwd()
    rec = {
        "resource": resource,
        "sid8": sid8,
        "worktree": worktree if worktree is not None else _detect_worktree(cwd),
        "branch": branch if branch is not None else _detect_branch(cwd),
        "claimed_at": time.time(),
        "host": socket.gethostname(),
        "pid": os.getpid(),
    }
    payload = json.dumps(rec)
    # Atomic first-claim.
    res = _cli("SET", key, payload, "NX", "EX", str(ttl))
    if res.upper() == "OK":
        return {"ok": True, "claimed": True, **rec}
    # Already held — inspect.
    cur = _cli("GET", key)
    holder = None
    if cur:
        try:
            holder = json.loads(cur)
        except Exception:
            holder = None
    if force or (holder and holder.get("sid8") == sid8):
        _cli("SET", key, payload, "EX", str(ttl))  # refresh / override
        return {"ok": True, "claimed": True, "refreshed": bool(holder and holder.get("sid8") == sid8),
                "forced": force and not (holder and holder.get("sid8") == sid8), **rec}
    return {"ok": False, "claimed": False, "resource": resource, "held_by": holder}


def release_lock(resource: str, sid8: str, *, force: bool = False) -> dict:
    """Release a resource. Owner-checked: only the holder (or --force) can drop
    it. Idempotent (releasing an unheld resource returns ok=True, existed=False)."""
    resource = _normalize_resource(resource)
    key = _lock_key(resource)
    cur = _cli("GET", key)
    if not cur:
        return {"ok": True, "existed": False, "resource": resource}
    try:
        holder = json.loads(cur)
    except Exception:
        holder = None
    if not force and holder and holder.get("sid8") != sid8:
        return {"ok": False, "existed": True, "resource": resource,
                "reason": "not owner", "held_by": holder}
    _cli("DEL", key)
    return {"ok": True, "existed": True, "resource": resource}


def list_locks() -> list[dict]:
    """All held locks, newest-claim first. Each gains `ttl_remaining` (s)."""
    keys_raw = _cli("--scan", "--pattern", f"{LOCK_PREFIX}*")
    keys = [k for k in keys_raw.splitlines() if k.strip()]
    out: list[dict] = []
    for key in keys:
        val = _cli("GET", key)
        if not val:
            continue
        try:
            rec = json.loads(val)
        except Exception:
            continue
        ttl = _cli("TTL", key)
        try:
            rec["ttl_remaining"] = int(ttl)
        except Exception:
            rec["ttl_remaining"] = None
        out.append(rec)
    out.sort(key=lambda r: r.get("claimed_at", 0), reverse=True)
    return out


# ── CLI ─────────────────────────────────────────────────────────────────────
def _resolve_sid8(args) -> str:
    if getattr(args, "from_hook", False):
        ev = _read_hook_stdin()
        sid = _sid8(ev.get("session_id", ""))
        if ev.get("cwd") and not os.environ.get("COORD_CWD"):
            os.environ["COORD_CWD"] = ev["cwd"]
        if sid:
            return sid
    if getattr(args, "sid8", None):
        return _sid8(args.sid8)
    return ""


def _cmd_presence(args) -> int:
    soft = getattr(args, "soft", False) or getattr(args, "from_hook", False)

    if args.action == "start":
        # SessionStart consumer: register + emit a context heads-up. Always
        # exit 0 (it's a hook); stay silent when alone or when Redis is down.
        sid8 = _resolve_sid8(args)
        if not sid8:
            return 0
        try:
            note = session_start(sid8, ttl=args.ttl)
        except CoordError as e:
            print(f"coord: redis unavailable, session_start skipped: {e}", file=sys.stderr)
            return 0
        if not note:
            return 0
        if getattr(args, "plain", False):
            print(note)
        else:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": note,
            }}))
        return 0

    if args.action == "list":
        try:
            recs = list_presence()
        except CoordError as e:
            print(json.dumps({"error": str(e)}))
            return 0 if soft else 1
        print(json.dumps(recs, indent=2 if not args.json else None))
        return 0

    sid8 = _resolve_sid8(args)
    if not sid8:
        print("coord: need --sid8 (or --from-hook with a session_id)", file=sys.stderr)
        return 0 if soft else 2

    try:
        if args.action == "register":
            rec = register(sid8, ttl=args.ttl)
        elif args.action == "heartbeat":
            rec = heartbeat(sid8, ttl=args.ttl)
        elif args.action == "release":
            ok = release(sid8)
            print(json.dumps({"released": sid8, "existed": ok}))
            return 0
        else:  # pragma: no cover
            print(f"coord: unknown action {args.action}", file=sys.stderr)
            return 2
    except CoordError as e:
        # A coordination layer must NEVER break the session it serves.
        print(f"coord: redis unavailable, presence {args.action} skipped: {e}",
              file=sys.stderr)
        return 0 if soft else 1
    print(json.dumps(rec))
    return 0


def _cmd_lock(args) -> int:
    soft = getattr(args, "soft", False)

    if args.action == "list":
        try:
            print(json.dumps(list_locks(), indent=2 if not args.json else None))
        except CoordError as e:
            print(json.dumps({"error": str(e)}))
            return 0 if soft else 1
        return 0

    sid8 = _resolve_sid8(args)
    if not sid8:
        print("coord: need --sid8 (or --from-hook)", file=sys.stderr)
        return 2
    try:
        if args.action == "claim":
            res = claim_lock(args.resource, sid8, ttl=args.ttl, force=args.force)
        elif args.action == "release":
            res = release_lock(args.resource, sid8, force=args.force)
        else:  # pragma: no cover
            print(f"coord: unknown action {args.action}", file=sys.stderr)
            return 2
    except CoordError as e:
        print(f"coord: redis unavailable, lock {args.action} skipped: {e}", file=sys.stderr)
        return 0 if soft else 1
    print(json.dumps(res))
    # claim that didn't get the lock -> nonzero so scripts can branch on it.
    return 0 if res.get("ok") else 3


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="coord", description=__doc__.split("\n")[1])
    sub = p.add_subparsers(dest="group", required=True)

    pres = sub.add_parser("presence", help="cross-session liveness (TTL keys)")
    pa = pres.add_subparsers(dest="action", required=True)

    for name in ("register", "heartbeat", "start"):
        sp = pa.add_parser(name)
        sp.add_argument("--sid8")
        sp.add_argument("--from-hook", action="store_true",
                        help="read session_id+cwd from a Claude hook JSON on stdin")
        sp.add_argument("--ttl", type=int, default=DEFAULT_PRESENCE_TTL)
        sp.add_argument("--soft", action="store_true",
                        help="exit 0 even if Redis is down (default on for --from-hook)")
        if name == "start":
            sp.add_argument("--plain", action="store_true",
                            help="print raw heads-up text instead of SessionStart JSON")
    rel = pa.add_parser("release")
    rel.add_argument("--sid8")
    rel.add_argument("--from-hook", action="store_true")
    rel.add_argument("--soft", action="store_true")
    lst = pa.add_parser("list")
    lst.add_argument("--json", action="store_true", help="compact (one-line) JSON")

    lock = sub.add_parser("lock", help="advisory resource claims (file/worktree)")
    la = lock.add_subparsers(dest="action", required=True)
    for name in ("claim", "release"):
        sp = la.add_parser(name)
        sp.add_argument("resource", help="path or arbitrary key (e.g. worktree:foo)")
        sp.add_argument("--sid8")
        sp.add_argument("--from-hook", action="store_true")
        sp.add_argument("--force", action="store_true",
                        help="override another holder (claim) / drop any holder (release)")
        sp.add_argument("--soft", action="store_true")
        if name == "claim":
            sp.add_argument("--ttl", type=int, default=DEFAULT_LOCK_TTL)
    llst = la.add_parser("list")
    llst.add_argument("--json", action="store_true")

    args = p.parse_args(argv)
    if args.group == "presence":
        return _cmd_presence(args)
    if args.group == "lock":
        return _cmd_lock(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
