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

Five kinds, all deliberate. This list is **derived, not recalled** — every
published file was diffed against its live original, and the result is the
accounting below: 44 byte-identical, 7 differing (enumerated here), 5 with no
live counterpart because this mirror wrote them (`README.md`, `PROVENANCE.md`,
`LICENSE`, `LICENSE-docs`, `.gitignore`). Two earlier versions of this section
claimed completeness and were wrong; stating the method is the repair, since
it makes the claim checkable rather than trusted.

**Synced against live at `29368ec`** (2026-08-04), superseding the `b92ac56`
pin. Naming the commit is deliberate: it turns "is this current?" from a
judgment into a diff anyone can run. **One file is knowingly behind it** — see
*Sync point*.

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
   table; contents byte-identical to live at the sync point — the divergence
   is the name, nothing else.

5. **A published tool with a deliberately unpublished dependency — 1 file.**
   `tools/disposition_sign.py` emits each brief disposition as a signed,
   chained peer-owned bobbin. Its signing path needs
   `bobbins._shared.{chain, peer_identity, peer_owned_bobbin}` and shells out
   to a second repository's interpreter (`$PARA_BOTS_ROOT`, default
   `~/para-bots`). **That repository is not published**, and deny-by-default
   means a file does not ship because something else references it. So the
   tool is here and its mechanism is not.

   This is disclosed rather than hidden because the failure is graceful and
   self-describing: with the dependency absent, `sign()` prints the missing
   interpreter, reports the event as recorded-but-NOT-signed, returns `None`,
   and never raises; the test suite runs 20 cases and skips 5 rather than
   failing. What survives publication is the *reasoning* — why a per-session
   ephemeral key rather than a standing fleet key, and why signing as a named
   peer would be forgery — which is the part with method value. Read it as an
   argument you can check, not a dependency you can install.

## Sync point

Four files had drifted behind live and were re-synced at `b92ac56`:
`tools/brief_sweep.py` (a crash on list-valued `topic` frontmatter, now
fixed), `tools/brief_disposition.py` and `conventions/brief_CONVENTION.md`
(both gained the `bounced` disposition kind), and `hololoom_mcp_README.md`
(re-measured orient cost figures). The full subset was re-gated on the new
bytes — secrets scan clean, no third-party-human disclosure, topology
unchanged at 20 accepted findings with zero absolute paths.

**The 2026-08-04 slice, and the gate that did not run.** That earlier sync
deliberately held back live's signing extension to `brief_disposition.py`,
because its dependency was unpublished. It now ships anyway, together with
`tools/disposition_sign.py` and `tools/test_disposition_sign.py` — divergence
kind 5 above — after the four mechanical gates passed on those exact bytes
(pinned by content hash in the private manifest, not by commit) and after
three disclosure questions were each ruled on individually: naming an AI peer
in the design rationale, publishing the key-store *location* the tests
reference, and shipping a tool whose mechanism stays private.

**The per-file human read — gate 4 of the five — was deliberately waived for
these three files.** It was not performed, and this is not a case of it being
performed lightly. The operator was offered the standard full-read
ratification, declined it, and chose to record a waiver instead. Everything
else in this repository carries that read; these do not. The distinction is
stated because *a gate you skipped and a gate you passed are different facts*,
and the audit trail is worth nothing if it flattens them. The one thing that
read has historically caught here — a live database password sitting in plain
sight where the automated secrets scan saw nothing unusual — is exactly the
class no mechanical gate covers.

**One file is knowingly behind the `29368ec` pin.**
`docs/how_this_repo_runs_itself.md` is 34 lines short of live, which added a
passage on negative-claim controls (`009cccb`, 2026-07-30). It is a pure
addition; nothing here was removed upstream. It was not re-synced because it
is the *first* slice's artifact under its own ratification, and this slice's
waiver does not reach it. Recorded rather than quietly reconciled.

That is the general shape: **this mirror is a pinned, self-consistent subset,
not a live tree.** Anything in `tools/` is best read as *how the method
works*, not as a maintained dependency.

References to files *outside* this subset are deliberately left as-is and
will not resolve. They name real parts of the private corpus; rewriting or
deleting them would misrepresent both what the method actually cites and what
was actually published.

---

*This emission was carried out slice by slice (an essay first, then this
curated subset), each ratified by the human operator before release. The
governing manifest and its full gate records live in the private corpus.*
