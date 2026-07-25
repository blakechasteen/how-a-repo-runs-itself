# Lens convention (`lens/*.md`)

A **lens** is a named, loadable reading context over the canon — a curated view
a session `hololoom_orient topic=<lens>` *into*. It is **fork A** of the
2026-06-20 design dialogue: a lens that narrows what you *read*, deliberately
**not** an org-chart, a routing unit, or a gate.

The load-bearing property: **a lens pre-loads; it never restricts.** Loading a
lens adds curated context — it does not stop a session from searching any corpus
or reading any pin. The moment a lens *gates* what a session may read, it has
become the org-chart we declined; pull back. (Same suggestion-not-directive
guard as WSH briefs — see `handoff/brief/_CONVENTION.md`.)

## Resolution

`hololoom_orient` lower-cases the `topic` hint and, if it **exactly** names a
`lens/<name>.md`, pre-loads that manifest into the brief as a `lens` block and
sets `topic_hint.lens = true`. When no lens matches, the existing fuzzy
thread/decision match is the fallback, unchanged — lenses are purely additive.
(Loader: `_load_lens` in `server.py`; override dir via `HOLOLOOM_LENS_DIR`.)

Files beginning with `_` (this one) never resolve as a lens — they lack a
`lens:` frontmatter key and the kebab-slug guard rejects the leading underscore.

## Frontmatter

| field | meaning |
|---|---|
| `lens` | the lens name (must equal the filename stem) — **required** |
| `description` | one-line summary |
| `status` | `active` / retired (forward-compat; not yet enforced) |
| `pins` | inline list of curated pin slugs — this lens's alternate spine |
| `briefs` | inline list of brief topics to surface (layered onto orient's brief set, deduped, capped) |
| `corpora` | inline list of default search corpora for the arc |
| `interpreted_by` / `sid8` / `originSessionId` | provenance (same discipline as memory pins) |

## What gets delivered

The prose body (everything after the frontmatter fence) becomes the `lens.context`
string in the orient brief. **Keep it arc-specific and lean** — the standing
truths a session working this arc needs in the background. General lens mechanics
live *here*, not in each manifest, so they aren't re-paid in every orient call.
The loader defensively truncates an over-long body (~2.2 KB) to protect the
orient token budget (watcher WARNs at 3500).

## Pins are a salience spine, not new content

A lens's `pins` are usually a **re-selection of pins already in `MEMORY.md`** —
the value is *salience* ("of your ~40 spine pins, these N matter for this arc")
plus the synthesized standing-context prose, not surfacing pins you lacked. A
lens only surfaces genuinely *unloaded* content when it points at
`catalog/CATALOG.md`-demoted pins (which a quieter arc's lens would). Both are
fine — just don't oversell the pin list as "context you'd otherwise miss."

## Taxonomy

Slice-1 lenses are hand-authored. The eventual lens taxonomy can be read off the
canon citation communities (`hololoom_canon op=community`) rather than invented —
that's the scaling story, deferred until more than one hand-authored lens earns
its keep.
