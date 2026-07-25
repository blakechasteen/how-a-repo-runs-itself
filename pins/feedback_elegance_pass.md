---
name: elegance pass before stacking features
description: User prefers pausing to refactor for elegance/extensibility before adding more features when boilerplate is accumulating across multiple modules
type: feedback
originSessionId: 74d158a1-bc6e-4091-9669-6685953da7bb
interpreted_by: claude-opus-4-7
---
When a multi-feature build accumulates duplication, or a new feature would have to land in 3+ existing modules, propose an elegance/extensibility pass *before* doing the feature.

Concrete triggers: indexer/writer/projection patterns repeated across files; per-corpus dispatch chains in if/elif/elif; a new corpus or collection is about to be added; a feature like Matrix-changelog needs to be wired into 3+ similar places.

**Why:** validated 2026-05-09 — I had Matrix changelog teed up to wire into 4 indexer files; user said "elegance and extensibility pass?" first. The refactor (`tools/_indexer.py` shared base + `Corpus` dataclass registry in `server.py`) took ~30 min and made adding the Matrix `on_complete` hook a one-line change in three places instead of three separate inline implementations. Reverse-order would have multiplied the wiring work.

**How to apply:** before launching into a multi-module feature, scan for the pattern. If three or more existing files would need similar but slightly-different additions, surface the refactor option as: "I can wire X into the four indexers directly OR pull the shared scaffolding into a base module first — the latter makes future-X cheaper. Which?" Then defer to the user's call. The elegance instinct often wins.
