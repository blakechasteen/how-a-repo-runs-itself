# Provenance — how this subset was emitted

This repository is not a dump. It is a **contracted emission**: a curated
subset of a private human–AI working corpus, released to the public under an
explicit, enumerated, human-ratified allowlist.

## The framing

The corpus treats **"the public" as a party**. Its governing rule is that
substrate crosses a party boundary only by *contracted emission*, never by
replication. So publishing wasn't "push some files" — it was writing a
contract (an allowlist manifest) with an unbounded counterparty and
satisfying it file by file.

- **Deny-by-default.** Nothing shipped unless it was individually enumerated
  on the allowlist. Sanitization is by *selection*, not by scrubbing a full
  corpus — an allowlist fails closed; redaction at corpus scale fails open.
- **Emission is one-way.** Permanence is assumed (caches, crawlers, model
  training). Taking the repo private later would limit further spread, not
  undo what is already out.

## The five gates (every file passed all five)

1. **Secrets scan** — mechanical (`gitleaks`) over the staged subset.
2. **Third-party-name scan** — human collaborators excluded unless they OK'd
   it; public-work citations kept as normal attribution.
3. **Provenance check** — every file's author-party is the human operator or
   the corpus's own indexers. Content authored by AI *peers* (their signed
   emissions) was **excluded**, pending a separate signed-consent release.
4. **Per-file human read** — the operator read every file, no sampling.
5. **Topology / service-disclosure scan** — hostnames, ports, paths, and
   container identifiers made explicit and consciously accepted or removed.

## What the gates caught

The per-file human read (gate 4) caught a hardcoded **default database
password** in two tools that the mechanical secret-scanner (gate 1) had
passed clean — it was an environment-variable *fallback default*, invisible
to the scanner as an ordinary string. A four-pattern re-audit confirmed it
was the only one. It was resolved by *changing the build input* (the public
copies use a `CHANGE_ME` placeholder), not by scrubbing.

That single event is the whole argument for the discipline: **a
mechanically-clean scan is not proof of safety.** The builder of a claim
cannot fully self-verify it; an independent read, and ideally an independent
reader, is what closes the gap.

## What was deliberately withheld

- All raw session transcripts and voice memos.
- Business/strategy and movement-positioning material.
- A threat-model document (publishing it would be self-defeating).
- Three memory pins that reference AI peers by their own words or narrated
  actions — deferred to a future release gated on those peers' signed
  consent.
- ~23 device- and environment-specific troubleshooting notes (real, but
  noise for a method audience).

## Divergence from the live system

Four kinds of deliberate divergence, plus one class of drift. This list is
**derived, not recalled** — every published file was diffed against its live
original, and the result is the accounting below: 40 byte-identical, 9
differing (enumerated here), 5 with no live counterpart because this mirror
wrote them (`README.md`, `PROVENANCE.md`, `LICENSE`, `LICENSE-docs`,
`.gitignore`). Two earlier versions of this section claimed completeness and
were wrong; stating the method is the repair, since it makes the claim
checkable rather than trusted.

1. **Genericized credential — 2 files.** `tools/spine_tier.py` and
   `tools/index_canon_graph.py` differ from their live originals by one line
   each: the database password default described above, replaced with
   `CHANGE_ME`.

2. **Flattened convention layout — 4 files.** In the live corpus the four
   `_CONVENTION.md` docs sit beside the things they govern (`handoff/brief/`,
   `handoff/inbox/`, `lens/`). Publishing those parents would have shipped a
   directory apiece to hold one file, so they were collected into
   `conventions/` and disambiguated by name — `brief_CONVENTION.md`,
   `inbox_CONVENTION.md`, `lens_CONVENTION.md`, `_capkip_CONVENTION.md`.
   Contents are otherwise unchanged. Where a published doc's *prose* refers to
   a bare `_CONVENTION.md` — including `_capkip_CONVENTION.md`'s remark about
   the `_` prefix carrying meaning, which this layout flattens away — it means
   the brief convention, here at `conventions/brief_CONVENTION.md`.

3. **Cross-reference paths repointed to match — 7 sites.** `CLAUDE.md` (4
   sites), `conventions/lens_CONVENTION.md` (1),
   `conventions/_capkip_CONVENTION.md` (1), and
   `conventions/brief_CONVENTION.md` (1) cited the live paths, which do not
   exist in this layout. Only the paths changed; no wording did.

4. **Spine README renamed — 1 file.** The repo's own README ships as
   `hololoom_mcp_README.md`, because the `README.md` at this mirror's root is
   a front door written for the mirror. Listed in that front door's file
   table; contents unchanged from live at cut time.

**Drift — 4 files are behind live.** The four above are deliberate. These are
not: the live corpus moved after this subset was staged, and the mirror was
not re-cut for it. Nothing sensitive is involved — the direction is simply
old, and it is disclosed rather than quietly reconciled.

- `tools/brief_sweep.py` — lacks a fix for a crash on list-valued `topic`
  frontmatter. **Run it and you may hit that bug**; live has it fixed.
- `tools/brief_disposition.py` and `conventions/brief_CONVENTION.md` — predate
  the `bounced` disposition kind, so the tool cannot record it and the
  convention does not document it.
- `hololoom_mcp_README.md` — its orient cost-composition figures were
  re-measured after the cut and are stale by roughly the amount that section
  itself warns about.

Re-syncing them would republish files whose human ratification was against
the earlier text, so the staleness is recorded here instead of silently
fixed. Anything in `tools/` is best read as *how the method works*, not as a
maintained dependency.

References to files *outside* this subset are deliberately left as-is and
will not resolve. They name real parts of the private corpus; rewriting or
deleting them would misrepresent both what the method actually cites and what
was actually published.

---

*This emission was carried out slice by slice (an essay first, then this
curated subset), each ratified by the human operator before release. The
governing manifest and its full gate records live in the private corpus.*
