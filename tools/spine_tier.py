#!/usr/bin/env python3
"""spine_tier.py — recompute the MEMORY.md spine/catalog tiering (composite hotness rule).

The 06-13 spine/catalog split (project_memory_spine_catalog_split) was a one-shot
snapshot, NOT self-maintaining: recency-active pins enter the always-loaded spine
correctly, age out of "active," and nothing ever demotes them — so the spine creeps
back toward the load cap (64 -> 78 entries in 11 days). This tool is the eviction
vent: it re-applies the rule on demand and surfaces what has gone cold.

Composite hotness rule — a spine entry STAYS iff ANY of:
  - top-of-canon          (TOP_CANON below; mirror of CLAUDE.md's operative list)
  - authored in-degree>=10 (live :CanonPin <-[:CITES]- count; excludes LLM :INVOKES)
  - user-lens             (slug starts user_)
  - operational guard     (slug starts feedback_)
  - active                (newest *authored* date in the pin <= WINDOW days old)
Everything else -> demote candidate (move the index line to catalog/CATALOG.md).

Honesty guarantees (project_memory_spine_catalog_split, project_intent_state_separation):
  * READ-ONLY by default — prints proposals; writes nothing without --apply.
  * --apply NEVER silently evicts: it skips any --hold slug (a human override of the
    rule — e.g. a low-in-degree pin you judge load-bearing) and reports the skip.
  * FAILS CLOSED: if the canon graph is unreachable, centrality is unknown, so the
    tool demotes NOTHING (a missing graph must not look like "everyone is cold").
    [[feedback_launchd_tools_run_under_system_py39]]: never silent-None into a benign bucket.
  * Contention-safe writes: asserts each moved line is present exactly once before
    rewriting (a concurrent edit aborts the move, nothing is written). Same posture
    as tools/_amend_spine.py. The memory Stop hook commits.

Authored-date, not git-date: recency is the newest YYYY-MM-DD token found inside the
pin body (creation + "AMENDED 2026-..." markers), capped at <= today so a future
tripwire date can't fake activity. This dodges the bulk-`git add .` contamination
that forced the original split to a ~10d git-date window.
[[feedback_memory_hook_attributes_committer_not_author]]

NOT auto-wired into /handoff — registering an always-on step is a separate greenlight
([[feedback_greenlight_scope_on_substrate_builds]]). Drop-in ready for it when wanted.
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import os
import re
import sys
from pathlib import Path

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
MEMORY_DIR = Path(
    os.environ.get(
        "HOLOLOOM_MEMORY_DIR",
        str(Path.home() / ".claude" / "projects"
            / str(_main_checkout_root()).replace("/", "-") / "memory"),
    )
)
MEMORY_MD = MEMORY_DIR / "MEMORY.md"
CATALOG_MD = MEMORY_DIR / "catalog" / "CATALOG.md"
HOLDS_MD = MEMORY_DIR / "catalog" / "HOLDS.md"  # durable, human-curated holds (see load_holds)
HOLD_RE = re.compile(r"^\s*-\s+`?(?P<slug>[a-z0-9_]+)`?")
HOLDS_HEADER = (
    "# Spine holds — the DURABLE form of `--hold`.\n"
    "#\n"
    "# Human-judged load-bearing pins the composite hotness rule would demote —\n"
    '# typically low-in-degree "false-cold" betweenness bridges that the in-degree\n'
    "# metric structurally under-counts. spine_tier keeps these with reason \"held\"\n"
    "# and never lists them as demotion candidates. One markdown bullet per hold,\n"
    "# WHY required (a hold carries its reason):\n"
    "#   - <slug> — <why + who + date>\n"
    "# Manage via: spine_tier.py --hold-add <slug> --why \"...\"   /   --hold-rm <slug>\n"
    "\n"
)

NEO4J_URI = os.environ.get(
    "HOLOLOOM_NEO4J_URI", os.environ.get("NEO4J_URL", "bolt://127.0.0.1:7687")
)
NEO4J_USER = os.environ.get("HOLOLOOM_NEO4J_USER", os.environ.get("NEO4J_USER", "neo4j"))
NEO4J_PASSWORD = os.environ.get(
    "HOLOLOOM_NEO4J_PASSWORD", os.environ.get("NEO4J_PASSWORD", "CHANGE_ME")
)

CENTRALITY_FLOOR = 10
DEFAULT_WINDOW_DAYS = 14

# Ebbinghaus graded-retention refinement (handoff/brief/ebbinghaus_decay_fold.md).
# A DRY-RUN INSTRUMENT ONLY: it scores a continuous retention alongside the binary
# active-window to see whether the graded curve would flip any real keep/demote
# verdict — it writes nothing and changes no tiering. INTERVAL_LADDER = the classic
# spaced-repetition optimal intervals; a pin's memory strength S grows with each
# distinct authored "review" (creation + AMENDED markers), so heavily-amended canon
# decays slowly and a write-once pin decays fast. R = e^(-age/S).
INTERVAL_LADDER = (1, 3, 7, 14, 30)   # days; S after 1..5+ reviews
DEFAULT_GRADED_THRESHOLD = 0.4        # R below this = attention-cold (the brief's example)

# Mirror of CLAUDE.md "Top-of-canon pins (the operative list)" + the READ FIRST..FIFTH
# foundational spine. Kept explicit (not marker-sniffed) so demotion of a foundational
# pin is impossible-by-construction even if its in-degree dips. Update WITH CLAUDE.md.
TOP_CANON = {
    "project_north_star",
    "project_autonomy_thesis",
    "project_myth_in_mythrl",
    "project_integration_discipline_lineage",
    "project_cat_human_relationship_as_success_canon",
    "project_autonomy_stack_name",
    "project_ai_side_substrate_primitives",
    "project_capability_asymmetry_mitigation",
    "project_architectural_safety_substrate",
    "project_substrate_as_constitution",
    "project_heavy_bobbin_protocol",
    "project_packs_ecosystems_architecture",
    "project_anvil_team_coordination_layer",
    "project_peer_contracting_unifies_privacy_economics",
}

BULLET_RE = re.compile(r"^- \[.*?\]\((?P<slug>[A-Za-z0-9_]+)\.md\)")
DATE_RE = re.compile(r"20\d{2}-[01]\d-[0-3]\d")
CATALOG_COUNT_RE = re.compile(r"(\d+)\s+lower-centrality")


def get_indegrees() -> dict[str, int] | None:
    """slug -> authored in-degree (incoming :CITES). None if the graph is unreachable."""
    try:
        from neo4j import GraphDatabase
    except Exception:
        return None
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as s:
            rows = s.run(
                "MATCH (p:CanonPin)<-[:CITES]-(:CanonPin) "
                "RETURN p.slug AS slug, count(*) AS deg"
            ).data()
        driver.close()
    except Exception as e:
        print(f"[spine_tier] canon graph unreachable ({e}); centrality UNKNOWN.", file=sys.stderr)
        return None
    return {r["slug"]: r["deg"] for r in rows if r.get("slug")}


def authored_dates(slug: str, today: dt.date) -> list[dt.date]:
    """Distinct YYYY-MM-DD tokens in the pin body, capped at <= today (ignore future
    tripwire/target dates), sorted ascending. Empty if the pin file is absent or carries
    no past date. These are the pin's 'review' events — creation + each AMENDED marker."""
    f = MEMORY_DIR / f"{slug}.md"
    if not f.exists():
        return []
    dates: set[dt.date] = set()
    for tok in DATE_RE.findall(f.read_text(encoding="utf-8", errors="replace")):
        try:
            d = dt.date.fromisoformat(tok)
        except ValueError:
            continue
        if d <= today:
            dates.add(d)
    return sorted(dates)


def newest_authored_date(slug: str, today: dt.date) -> dt.date | None:
    """Newest authored date in the pin body (<= today). None if none. See authored_dates."""
    ds = authored_dates(slug, today)
    return ds[-1] if ds else None


def graded_retention(slug: str, today: dt.date) -> tuple[float | None, int, dt.date | None]:
    """Ebbinghaus retention R = e^(-age/S) for a pin (DRY-RUN instrument — see the
    INTERVAL_LADDER note). age = days since the newest authored date (last 'review');
    S = INTERVAL_LADDER[min(n_reviews, 5) - 1], memory strength growing with the number
    of distinct authored review-days. Returns (R, n_reviews, newest); R is None when the
    pin carries no past date (undated -> the same 'no-date' bucket the binary rule uses)."""
    ds = authored_dates(slug, today)
    if not ds:
        return None, 0, None
    n_reviews = len(ds)
    newest = ds[-1]
    age = (today - newest).days
    S = INTERVAL_LADDER[min(n_reviews, len(INTERVAL_LADDER)) - 1]
    return math.exp(-age / S), n_reviews, newest


def parse_spine() -> list[tuple[int, str, str]]:
    """Return [(line_index, slug, raw_line)] for every bullet pin entry in MEMORY.md."""
    out = []
    for i, line in enumerate(MEMORY_MD.read_text(encoding="utf-8").splitlines()):
        m = BULLET_RE.match(line)
        if m:
            out.append((i, m.group("slug"), line))
    return out


def classify(slug: str, today: dt.date, window: int, indeg: dict[str, int] | None,
             holds: set[str] | None = None):
    """(keep: bool, reason: str). Order matters — first matching keep-criterion wins;
    centrality is checked LAST so an unknown graph fails closed to keep. A durable
    hold (catalog/HOLDS.md) is the human override and wins first."""
    if holds and slug in holds:
        return True, "held"
    if slug in TOP_CANON:
        return True, "top-canon"
    if slug.startswith("user_"):
        return True, "user-lens"
    if slug.startswith("feedback_"):
        return True, "guard"
    newest = newest_authored_date(slug, today)
    if newest is not None and (today - newest).days <= window:
        return True, f"active({newest}, {(today - newest).days}d)"
    if indeg is None:
        return True, "centrality-unknown(fail-closed-keep)"
    deg = indeg.get(slug, 0)
    if deg >= CENTRALITY_FLOOR:
        return True, f"central(indeg={deg})"
    age = "no-date" if newest is None else f"{(today - newest).days}d"
    return False, f"cold(indeg={deg}, newest={newest}, age={age})"


def run_graded_dryrun(spine, today: dt.date, window: int, threshold: float,
                      indeg: dict[str, int] | None, holds: set[str]) -> int:
    """READ-ONLY Ebbinghaus dry-run (writes NOTHING, ignores --apply). Scores continuous
    retention R=e^(-age/S) alongside the binary active-window and reports where the two
    would FLIP a keep/demote verdict — the demand signal for
    handoff/brief/ebbinghaus_decay_fold.md. A verdict can only flip for a pin held by
    NEITHER a categorical rule (held/top-canon/user-lens/guard) NOR centrality
    (indeg>=FLOOR) — those are the pins where the recency predicate is load-bearing.
    Build the graded upgrade only if these flips are real mis-calls; decline if graded
    reproduces the binary decision everywhere."""
    rows, categorical = [], 0
    for _, slug, _ in spine:
        if slug in holds or slug in TOP_CANON or slug.startswith("user_") or slug.startswith("feedback_"):
            categorical += 1
            continue
        newest = newest_authored_date(slug, today)
        age = None if newest is None else (today - newest).days
        binary_active = age is not None and age <= window
        R, n_rev, _ = graded_retention(slug, today)
        graded_active = R is not None and R >= threshold
        deg = 0 if indeg is None else indeg.get(slug, 0)
        central = indeg is None or deg >= CENTRALITY_FLOOR   # fail-closed keep when graph down
        bk, gk = binary_active or central, graded_active or central
        rows.append(dict(slug=slug, n=n_rev, newest=newest, age=age, R=R, deg=deg,
                         central=central, ba=binary_active, ga=graded_active,
                         bk=bk, gk=gk, flip=bk != gk))

    graph_state = "UNREACHABLE" if indeg is None else f"live({len(indeg)})"
    print("EBBINGHAUS GRADED-RETENTION DRY-RUN (read-only — writes nothing, ignores --apply)")
    print(f"  spine={len(spine)}  window={window}d  threshold R>={threshold}  ladder={INTERVAL_LADDER}  today={today}")
    print(f"  canon graph: {graph_state}   categorical-kept(unaffected)={categorical}   recency-population={len(rows)}")

    if indeg is None:
        print("\n  ⚠ graph UNREACHABLE -> centrality fail-closes EVERY pin to KEEP under both scorers,")
        print("    so any '0 flips' is an ARTIFACT, not agreement. Re-run with a live graph (sandbox OFF)")
        print("    to assess. No verdict. [[feedback_sandboxed_bash_localhost_false_down]]")
        return 0

    flips = [r for r in rows if r["flip"]]
    rescues = [r for r in flips if r["gk"] and not r["bk"]]   # graded keeps what the window demotes
    sooner = [r for r in flips if r["bk"] and not r["gk"]]    # graded demotes what the window keeps
    central_kept = sum(1 for r in rows if r["central"])
    print(f"  central-kept(indeg>={CENTRALITY_FLOOR}, recency moot)={central_kept}   "
          f"recency-decided={len(rows) - central_kept}\n")

    if not flips:
        print(f"NO FLIPS — graded reproduces the binary keep/demote verdict on all {len(rows)} "
              f"non-categorical pins.")
        print("=> DECLINE signal: the binary window already captures the recency signal; graded adds none.")
        return 0

    def fmt(r) -> str:
        Rs = "  —  " if r["R"] is None else f"{r['R']:.3f}"
        ages = "no-date" if r["age"] is None else f"{r['age']}d"
        kind = "RESCUE" if (r["gk"] and not r["bk"]) else "DEMOTE-SOONER"
        return (f"  {r['slug']:<50} n={r['n']:<2} age={ages:<8} R={Rs}  indeg={r['deg']:<3} "
                f"bin={'A' if r['ba'] else '.'} grd={'A' if r['ga'] else '.'}  {kind}")

    print(f"FLIPS ({len(flips)} of {len(rows)} recency pins — graded ≠ binary verdict):")
    print(f"  ── RESCUES ({len(rescues)}: heavily-reviewed pins the {window}d window demotes, graded keeps) ──")
    for r in sorted(rescues, key=lambda r: -(r["R"] or 0)):
        print(fmt(r))
    print(f"  ── DEMOTE-SOONER ({len(sooner)}: shallow recent pins the window keeps, graded demotes) ──")
    for r in sorted(sooner, key=lambda r: (r["R"] or 0)):
        print(fmt(r))
    print(f"\n=> DEMAND SIGNAL: graded flips {len(flips)} verdict(s) ({len(rescues)} rescue / {len(sooner)} demote-sooner).")
    print("   Judge whether those calls are BETTER than the binary window (=> build) or noise (=> decline).")
    return 0


def apply_demotions(to_move: list[tuple[int, str, str]]) -> None:
    """Move each (idx, slug, line) from MEMORY.md into CATALOG.md. Contention-safe:
    asserts each line is present exactly once in MEMORY.md before any write."""
    mem = MEMORY_MD.read_text(encoding="utf-8")
    for _, slug, line in to_move:
        n = mem.count(line + "\n")
        if n != 1:
            print(f"ABORT: spine line for {slug} present {n}x (expected 1) — not writing.")
            print(f"  line: {line[:70]}...")
            sys.exit(2)
    # Remove from spine.
    for _, _, line in to_move:
        mem = mem.replace(line + "\n", "", 1)
    # Update the catalog-count in the footer note (best-effort; honesty only).
    cat = CATALOG_MD.read_text(encoding="utf-8")
    new_cat_count = sum(1 for ln in cat.splitlines() if BULLET_RE.match(ln)) + len(to_move)
    mem = CATALOG_COUNT_RE.sub(f"{new_cat_count} lower-centrality", mem, count=1)
    # Append to catalog (flat list; recall-reachable, order-insensitive).
    cat = cat.rstrip("\n") + "\n" + "\n".join(line for _, _, line in to_move) + "\n"
    MEMORY_MD.write_text(mem, encoding="utf-8")
    CATALOG_MD.write_text(cat, encoding="utf-8")


def load_holds() -> set[str]:
    """Durable, human-curated holds — the persistent sibling of `--hold`. Slugs the
    composite hotness rule would demote but a human judged load-bearing (typically
    low-in-degree 'false-cold' betweenness bridges the in-degree metric under-counts).
    One markdown bullet per hold in catalog/HOLDS.md. A missing file or a malformed
    line just means that slug is absent — fail-open to the rule, never crash."""
    if not HOLDS_MD.exists():
        return set()
    out: set[str] = set()
    for line in HOLDS_MD.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = HOLD_RE.match(line)
        if m:
            out.add(m.group("slug"))
    return out


def hold_add(slug: str, why: str) -> int:
    """Append a durable hold (creating HOLDS.md with its header if absent). Idempotent;
    reported, never silent (INV: a hold carries its WHY)."""
    if slug in load_holds():
        print(f"already held: {slug}")
        return 0
    HOLDS_MD.parent.mkdir(parents=True, exist_ok=True)
    if not HOLDS_MD.exists():
        HOLDS_MD.write_text(HOLDS_HEADER, encoding="utf-8")
    with HOLDS_MD.open("a", encoding="utf-8") as f:
        f.write(f"- {slug} — {why}\n")
    print(f"held: {slug} — {why}")
    return 0


def hold_rm(slug: str) -> int:
    """Remove a durable hold (the human override's off-switch — reported, never silent)."""
    if not HOLDS_MD.exists():
        print("no holds file — nothing to remove")
        return 0
    lines = HOLDS_MD.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [ln for ln in lines
            if ln.lstrip().startswith("#") or not (HOLD_RE.match(ln) and HOLD_RE.match(ln).group("slug") == slug)]
    if len(kept) == len(lines):
        print(f"not held: {slug}")
        return 0
    HOLDS_MD.write_text("".join(kept), encoding="utf-8")
    print(f"unheld: {slug}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="move demoted lines (default: print only)")
    ap.add_argument("--hold", default="", help="comma-separated slugs to KEEP for THIS run only (ephemeral; for a durable hold use --hold-add)")
    ap.add_argument("--hold-add", default="", metavar="SLUG", help="add SLUG to the durable holds list (catalog/HOLDS.md); requires --why")
    ap.add_argument("--hold-rm", default="", metavar="SLUG", help="remove SLUG from the durable holds list")
    ap.add_argument("--why", default="", help="rationale for --hold-add (a durable hold carries its reason)")
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW_DAYS, help=f"active-recency window in days (default {DEFAULT_WINDOW_DAYS})")
    ap.add_argument("--today", default="", help="override today (YYYY-MM-DD) for reproducible runs")
    ap.add_argument("--graded", action="store_true", help="READ-ONLY Ebbinghaus dry-run: score continuous retention R=e^(-t/S) alongside the binary active-window and report keep/demote FLIPS (writes nothing; ignores --apply). See handoff/brief/ebbinghaus_decay_fold.md")
    ap.add_argument("--graded-threshold", type=float, default=DEFAULT_GRADED_THRESHOLD, help=f"retention R below which a pin is attention-cold (default {DEFAULT_GRADED_THRESHOLD})")
    args = ap.parse_args()

    if args.hold_add:
        if not args.why.strip():
            print("--hold-add requires --why (a durable hold carries its reason)")
            return 2
        return hold_add(args.hold_add.strip(), args.why.strip())
    if args.hold_rm:
        return hold_rm(args.hold_rm.strip())

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    hold = {s.strip() for s in args.hold.split(",") if s.strip()}
    holds = load_holds()          # durable holds (catalog/HOLDS.md) — the persistent override
    indeg = get_indegrees()

    spine = parse_spine()

    if args.graded:
        if args.apply:
            print("(note) --graded is a read-only dry-run; --apply is ignored.\n")
        return run_graded_dryrun(spine, today, args.window, args.graded_threshold, indeg, holds)

    demote, kept_summary = [], {}
    for idx, slug, line in spine:
        keep, reason = classify(slug, today, args.window, indeg, holds)
        if keep:
            kept_summary[reason.split("(")[0]] = kept_summary.get(reason.split("(")[0], 0) + 1
        else:
            demote.append((idx, slug, line, reason))

    graph_state = "UNREACHABLE (fail-closed: demoting nothing)" if indeg is None else f"live ({len(indeg)} pins)"
    print(f"spine entries: {len(spine)}   window: {args.window}d   today: {today}   canon graph: {graph_state}")
    print("kept by: " + ", ".join(f"{k}={v}" for k, v in sorted(kept_summary.items(), key=lambda x: -x[1])))
    print()
    if not demote:
        print("No demotion candidates — spine is clean by the rule.")
        return 0

    print(f"DEMOTION CANDIDATES ({len(demote)}):")
    for _, slug, _, reason in demote:
        held = " [HELD — kept by --hold]" if slug in hold else ""
        print(f"  {'KEEP ' if slug in hold else 'MOVE '} {slug:<52} {reason}{held}")

    to_move = [(i, s, l) for (i, s, l, _) in demote if s not in hold]
    if not args.apply:
        print(f"\n(dry-run) {len(to_move)} would move to catalog, {len(demote) - len(to_move)} held. Re-run with --apply.")
        return 0

    if not to_move:
        print("\nAll candidates are held — nothing to move.")
        return 0
    apply_demotions(to_move)
    print(f"\nAPPLIED: moved {len(to_move)} entries MEMORY.md -> catalog/CATALOG.md ({len(demote) - len(to_move)} held).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
