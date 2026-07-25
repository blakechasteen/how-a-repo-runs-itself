---
name: Probe before designing any read-side build
description: In HoloLoom-style multi-writer systems, canon describes write intent but not write distributions. Run a P0-style probe (counts + samples + prototype scan) before scoping any read-side vertical. Two consecutive 2026-05-09 probes (HippoRAG, CITES) caught major design pivots before code shipped.
type: feedback
originSessionId: cb24e850-ecc0-47aa-bd22-fbc22752b873
interpreted_by: claude-opus-4-7
---
**Rule.** Before scoping any read-side build vertical (a navigator, an
extractor, a graph algorithm) in HoloLoom-style multi-writer systems,
write a P0 probe and run it against live state. Use the data to design,
not the canon.

**Why.** In long-lived systems with multiple independent writers (Para's
materializer, structured Bobbin spinners, MCP indexers, yarn_writer),
documentation describes write *paths* but not write *distributions*.
Operational reality drifts from design intent. The drift is invisible
until probed.

Two precedents in one 2026-05-09 session:

- **HippoRAG P0c**: probe of `:Entity`/`:Concept`/MENTIONS state showed
  `:Concept` dominates 525:13 over `:Entity`, dedupe race produced two
  `'digest'` :Entity nodes, `:Concept.aliases` already exists as a
  built-in synonym mechanism. Original spec assumed `:Entity`-primary
  + new SYNONYM_OF as the synonym mechanism. Probe forced revision to
  `:Concept`-primary + use existing aliases + add P0d uniqueness
  constraints before backfill.
- **CITES P0c**: probe of `:DocChunk`→`:CodeSymbol` citation density
  found near-zero yield (0 dotted-qualname matches in 30 chunks; 9
  bare-class matches in 100 chunks with 0 in inline-code context).
  Inline-code ground truth showed docs cite **file paths** (12% of
  chunks) and **Neo4j labels** (`Session`, `Utterance` map to schema
  kinds, NOT to `:Concept` nodes). Original spec scoped to
  CodeSymbol-CITES would have built infrastructure with no signal.
  Probe forced narrow to `:File` REFERENCES as the only buildable-now
  vertical.

**How to apply.**

1. **Always write a probe.py before extractor/navigator code.** Live
   counts of every node label and edge type the build expects to use.
   Random samples to inform regex / matching heuristics. Prototype
   scan against current substrate to estimate yield per unit.

2. **State pre-probe predictions and outcome thresholds.** Before
   running, write down: "if yield is >X, P1 is justified; if Y-X,
   scope down; if <Y, kill original scope, investigate what shape
   actually appears." Makes falsification productive instead of
   retroactive.

3. **Capture probe findings in SESSION.json + amend SPEC.** Don't
   bury them in chat history. Future-Claude reads SESSION.json on
   orient; that's where intent-vs-reality discoveries belong. SPEC
   amendment shows the design history honestly.

4. **Promote the probe to a recurring check when build lands.** A
   one-shot probe is a substrate snapshot. The same script run on
   cadence (launchd cron) becomes drift detection. Probes graduate
   from "build prerequisite" to "system honesty primitive."

**When this rule does NOT apply.** Pure code-internal builds (algorithm
on already-known data shapes, refactors, performance work). The probe
discipline is specifically for *read-side over emergent multi-writer
substrate* — anywhere the question "what does the data actually look
like" might surprise you.
