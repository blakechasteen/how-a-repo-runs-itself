#!/usr/bin/env bash
# wt-venv.sh — make a worktree's hololoom_mcp/ runnable.
#
# .venv/ is gitignored, so a fresh `EnterWorktree` checkout has no virtualenv
# and Python/tests won't run. This symlinks the canonical .venv from the main
# checkout into the current worktree, so `./.venv/bin/python` and
# `PYTHONPATH=. ./.venv/bin/python ...` behave exactly as they do on main
# (main's site-packages, the worktree's source via PYTHONPATH=.).
#
# Run once, from the worktree's hololoom_mcp/ directory, right after entering
# the worktree. Idempotent.
#
# CANONICAL_VENV is derived, not hardcoded, so this script carries no operator
# username and survives the repo moving (Gate 5, 2026-07-25). --git-common-dir
# resolves to the PRIMARY checkout's .git from inside any worktree, which is
# exactly the "canonical" the name means. (The launchd plists still hardcode
# the path; they are not shell and are out of this script's reach.)
set -euo pipefail
CANONICAL_VENV="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")/hololoom_mcp/.venv"

if [ ! -d "$CANONICAL_VENV" ]; then
  echo "wt-venv: canonical .venv missing at $CANONICAL_VENV" >&2
  exit 1
fi
if [ -e .venv ]; then
  echo "wt-venv: .venv already present here — nothing to do"
  exit 0
fi
if [ "$(pwd -P)" = "$(dirname "$CANONICAL_VENV")" ]; then
  echo "wt-venv: you're in the MAIN checkout, not a worktree — refusing" >&2
  exit 1
fi
ln -s "$CANONICAL_VENV" .venv
echo "wt-venv: linked .venv -> $CANONICAL_VENV"
