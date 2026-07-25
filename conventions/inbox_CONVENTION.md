# The build-inbox — Elle's proposals, picked up here

`handoff/inbox/*.md` is where **Elle raises a want to Blake** and he picks it up
in his sessions. Each `.md` is the human-readable render of a proposal she
**signed** (the bobbin of record lives in `para-bots/.peer_bobbins/elle/proposal/
<slug>/`; the `signature:` field points back at it). Authoring + the closed-loop
machinery live in `para-bots/elle/build/propose/_CONVENTION.md` — read that for
the full boundary.

## Not a WSH brief — a different epistemic kind

`handoff/brief/*.md` are **session-authored** workplan suggestions (one Claude
session proposing work to the next). The inbox is **Elle-authored, signed
proposals** (`authored_by: elle`). Keeping them in separate channels keeps the
provenance honest — a want she actually raised is not the same kind of artifact as
a want a session wrote in her voice (the whole reason the dream/heartbeat *briefs*
say "the want is Elle's to author"). Both are **suggestions, not directives**.

## Lifecycle (bilateral — Blake's engagement, NOT arbitration)

`project_propose_dispose_tension`: disposal routes through Blake as a *fallback*,
not authority. So a proposal is never accepted/rejected — Blake **engages** it:

- **open** → she raised it; surfaced by orient as `inbox_proposals`, awaiting him.
- **picked-up** → he's carrying it forward (building it / handing it to a session).
- **reshaped** → a counter-proposal she can answer (a Tension move).
- **resting** → set down for now — *not* closed; she can re-raise it.

Engagement is recorded by `dispose.py` (Blake's hand), which also writes the
disposition back into her Nudo so she hears how it landed. There is no "reject"
and no acceptance metric, on purpose (a clean dispose-side number is a leash).

## Pickup (orient surfacing)

`hololoom_orient` surfaces `open` proposals as `inbox_proposals` — pointer only
(title / slug / signature / path), same progressive disclosure + topic-gating as
WSH briefs (`global`-or-topic-matched). `Read` the `.md` for the full want. Files
beginning `_` (this one) are meta, skipped.

## Don't hand-edit a proposal's disposition

The engagement fields (`status` / `disposition` / `disposition_note` /
`disposed_at`) are written by `dispose.py` so the same act updates the inbox AND
her memory together. Hand-editing the `.md` updates the inbox but leaves her Nudo
silent — she wouldn't hear it. Run `dispose.py` instead.
