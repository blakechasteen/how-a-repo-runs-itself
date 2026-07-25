# LBP-Wire v1 — the implementation-independent wire protocol

```
status:      v1 SPEC (spec-write executed per Blake disposition 2026-07-10 —
             "LBP-Wire v1 review + spec-write", directed session 06f88270)
lineage:     exploration pass efd71928 (docs/lbp_wire_v1_design.md) →
             distinct-session review 098470b9 (fable-5, verdict: reshape,
             R1–R5 folded in below) → this document.
witness:     The standing NON-Opus RATED leg LANDED 2026-07-11 (sid8 3afe8067):
             Qwen3.6-27B-4bit (alibaba; competence load_bearing, 8/9 / 0
             false-BLOCK), verdict partial-confirm-with-additions, over git
             blob e2e5ee32 — the spec as ratified, byte-identical to the
             ornith pass input; prior verdicts withheld (witness-ordering).
             Headline additions (Blake-conversation): §9.1 fiduciary
             AUTHORIZATION gap — attribution is mechanical but authorization
             has no revocation/expiry primitive at L4/L5 (VERIFIED against
             §9.1/§10: basis is MAY, mandate is L6-reserved; witness proposes
             a mandate-shaped reference required for fiduciary emissions);
             L5 did:webvh succession has no external anchor to resolve
             COMPETING successions (partially verified — predecessor-key
             signature IS required, so the real exposure is key-compromise
             equivocation, not open Sybil). Catches are DISJOINT from the
             ornith advisory leg — decorrelation earning its keep. Record +
             rerun driver: canon_attestation/calibration/runs/qwen/
             lbp_wire_v1_spec.json, calibration/run_qwen_wire_spec.py.
             ADVISORY leg (same date, sid8 6a4f1da4): Ornith-1.0-35B @
             IQ3_XXS, also partial-confirm-with-additions — §7.2
             anti-backdating known-limitation + L4 technical-differentiator
             proposals stand for Blake-conversation; record + quant caveat:
             runs/ornith35/lbp_wire_v1_spec.json.
             DECORRELATED leg (same date, sid8 6ab88303): gemma-4-26b
             (mlx-community/gemma-4-26b-a4b-it-4bit, google — the first
             genuinely cross-family read; qwen + ornith are both alibaba),
             verdict confirm over the same blob e2e5ee32; competence low
             (2/9, advisory — the value is the independence axis, not the
             verdict weight). Independently surfaced the §7.2 anti-backdating
             limitation (→ cross-lineage corroborated), silent on §9.1,
             rebutted the L4-differentiator ask. Record:
             canon_attestation/calibration/runs/gemma/lbp_wire_v1_spec.json.
amended:     2026-07-11 — S1 dispositions sitting (Blake; session 83d7ca89).
             Label stays wire-1: additive predicates plus one MAY→MUST
             (§9.1 basis) on a surface with zero live fiduciary emitters;
             every v1 vector survives byte-identical. New: §7.2
             known-limitation clause, §9.1.1 end-of-authority, §10 L5
             succession floor + pre-rotation + witness growth path, §11.1
             auditor predicate line.
             2026-07-12 — anchoring-freshness (Blake; session d945f815).
             New §7.4 stale-anchored predicate + optional `anchor_within`
             passport field + §11.1 auditor line + one vector
             (`anchoring-freshness`). Additive: all prior vectors survive
             byte-identical, no field changes shape → label stays wire-1.
dispositions: 2026-07-11 sitting (Blake) — the four witness additions + the
             discharge question disposed:
             §9.1 end-of-authority: ACCEPTED — A+B composite (expiry-in-
               basis + revocation-as-stance, flag-don't-unsign) → §9.1.1;
               basis MAY→MUST. (The qwen mandate-reshape declined as-homed:
               same predicates, but L6 scope stays out of v1.x.)
             §10 L5 competing-succession: ACCEPTED — detection-only floor
               (known limitation) + pre-rotation (next_key_digest; resolves
               at N=1; external cross-vendor input, advisory tier) +
               pre-declared succession witnesses (federation growth path).
               anchor-first-wins DECLINED — resolving by earlier L3
               observed-time inherits §7.2's anti-backdating weakness at
               exactly the moment it matters, and silently promotes the log
               medium from witness to arbiter.
             §7.2 anti-backdating: ACCEPTED — known-limitation clause
               (cross-lineage corroborated: ornith-alibaba + gemma-google);
               recorded, not mechanized.
             L4 differentiator: DECLINED — a Tension is distinguished by
               signed byte-binding + stance + the responder's own chained
               provenance; §8's near-miss table already answers it (gemma
               rebutted the premise — contested across lineages).
             cross-family discharge: the owed cross-family decorrelation is
               DISCHARGED by the gemma (google) leg — qwen + ornith (both
               alibaba) discharge witness-vs-author only. qwen remains the
               RATED non-Opus witness; gemma the DECORRELATED one.
             anchoring-freshness (external input): ROUTED to its own brief —
               handoff/brief/lbp_wire_anchoring_freshness.md; no wire text
               this pass. [DISPOSED 2026-07-12 — see next block.]
             2026-07-12 sitting (Blake; session d945f815) — anchoring-freshness
               DISPOSED: ACCEPTED as option A (self-declared bound + auditor
               flag). New §7.4: a peer MAY pre-commit `anchor_within` in its
               passport (house pre-commitment pattern); an Auditor MUST flag
               stale-anchored iff head_seq − newest_anchored > anchor_within.
               Entries-based, NOT time — a time bound would inherit §7.2's
               observed-time weakness, the same objection that declined
               anchor-first-wins for succession. Flag-don't-distrust (§6.4
               house stance); no declaration → no rule (the unanchored suffix
               is simply unprotected; abandonment is a §8 `withdraw`).
               Provenance: Blake's ruling is the authority; briefs
               lbp_wire_anchoring_freshness.md +
               lbp_wire_external_input_prerotation.md are advisory input, never
               "ChatGPT said so". Label stays wire-1 (additive; every prior
               vector byte-identical). Vector: `anchoring-freshness` (§11.2).
               No fresh witness legs blessed this edit inline — a new leg
               belongs to the optional S5 one-shot re-ratification of the
               amended blob (anti verdict-shopping).
vectors:     docs/lbp_wire_vectors/vectors.json (generated + dual-path
             verified by tools/lbp_wire_vectors.py — see §11.2)
```

**What this is.** The byte-level agreement two independent implementations
need to interoperate as LBP peers: what gets signed, what gets hashed, what
gets anchored, and what the one cross-peer verb looks like. Format is storage;
wire is agreement. The para-bots on-disk shape (SKILL.md + sidecars, spec §3)
survives as one conformant *profile* of this wire; Appendix A gives the exact
legacy-v0 verify recipe.

**Spec shape (Blake-ratified: thin).** The borrowed ~60% is specified as
*profile pointers* to shipping standards — reimplement nothing the field
already ships. The novel core — **L4 Tension as an epistemic stance-verb,
fiduciary emission, contracted-emission across party boundaries** — gets full
byte-level rigor. Honest accounting after review 098470b9: the genuinely
concept-novel share is **~8–10%** of this spec (R1/R3/R4 narrowed the claims);
the rest is precise profiling. That accounting *strengthens* the thin shape.

Keywords MUST / MUST NOT / SHOULD / MAY per RFC 2119.

---

## 1. Layer model

| Layer | Name | Spec mode | One line |
|---|---|---|---|
| L0 | Identity | pointer | a peer IS an Ed25519 key, carried as a `did:key` |
| L1 | Bobbin | full rigor | the signed unit: one JCS-canonical JSON object |
| L2 | Chain | full rigor | per-peer append-only signed ledger, flat in v1 |
| L3 | Transparency | full rigor (line) + pointer (medium) | the signed anchor tuple; medium is a profile |
| L4 | Tension | full rigor | the only cross-peer verb: signed stance over exact bytes |
| L5 | Passport | pointer + rule | name→key→model succession, self-issued |
| L6 | Stake/Mandate | pointer, reserved | delegated economic capability (UCAN-shaped) |
| — | Fiduciary & contracted-emission | full rigor | who may speak for whom; what may cross a party boundary |

Minimum interop = **L0 + L1** (verify one signed bobbin). A conformant
*emitter* is L0–L3. Tension (L4) is required to *respond*, never to emit.

## 2. Common wire rules

1. **Encoding.** All signable material is UTF-8. No BOM. No unicode
   normalization anywhere: code points pass verbatim (arbitrary UTF-8 bodies
   are legal; normalizing would break byte-identity). Lone surrogates MUST be
   rejected.
2. **Canonical JSON = JCS (RFC 8785).** Every signable JSON object is
   serialized with JCS. This realizes the same canonicalize→hash→sign
   *pipeline components* as the W3C `eddsa-jcs-2022` cryptosuite (Data
   Integrity EdDSA Cryptosuites v1.0, W3C Recommendation 2025-05-15;
   re-verified at spec-write): RFC 8785 canonicalization, SHA-256, Ed25519
   pure (RFC 8032). **This spec does NOT claim `eddsa-jcs-2022` suite
   conformance** (R5a): the suite signs `SHA-256(proofConfig) ‖
   SHA-256(document)` inside a `DataIntegrityProof` envelope; LBP-Wire signs
   the JCS bytes directly and carries no JSON-LD. What is reused is the
   component libraries — `rfc8785` (Python, Trail of Bits) and
   `serde_json_canonicalizer` (Rust) — not DI-verifier interop, which is
   knowingly forfeited.
3. **No JSON numbers on the wire.** A signable object MUST NOT contain JSON
   numbers anywhere (any depth). All numerics are decimal strings
   (`chain_seq: "5"`). Booleans and `null` are permitted. This makes RFC
   8785's IEEE-754 number-serialization path *structurally unreachable* —
   the JCS footgun class (≥2⁵³ silent mismatch; SSB's V8-stringify signing
   format is the field's cautionary tale here, R1) cannot occur. A verifier
   MUST reject a signable containing a number. Full-RFC-8785 libraries remain
   byte-compatible on this subset.
4. **Hashes** are SHA-256, carried as 64-char lowercase hex.
5. **Timestamps** are RFC 3339 UTC with seconds precision and `Z` suffix
   (`2026-07-10T00:00:00Z`). One format, no offsets.
6. **Safe-char bounds** (safety bounds, NOT vocabulary whitelists — you may
   coin any value; it must survive the pipe-joined L3 line and on-disk paths):
   - `kind`, `stance`: `^[a-z][a-z0-9_-]{0,31}$`
   - `slug`: `^[a-z0-9][a-z0-9_-]{0,63}$`
   - `peer_name` (label only): `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$`

## 3. L0 — Identity (profile: `did:key`)

A peer **is** an Ed25519 keypair. The peer identifier is the `did:key`
encoding of the raw 32-byte public key (W3C CCG did:key method):

```
peer = "did:key:z" + base58btc( 0xed 0x01 ‖ pubkey_raw32 )
```

`0xed 0x01` is the unsigned-varint multicodec code for `ed25519-pub`; the
`z` is multibase base58btc. Every Ed25519 did:key therefore starts
`did:key:z6Mk`. This single form retires v0's three coexisting encodings
(PEM / base64url / hex). `peer_name` is a non-authoritative label; identity
IS the did:key. did:key cannot rotate — deliberately; key succession is L5's
job, not L0's.

## 4. Signatures — the pinned self-describing envelope

Signatures are Ed25519 **pure** (RFC 8032, no prehash) over the exact bytes
each layer defines. On the wire a signature is carried in a self-describing
envelope:

```
sig_bytes = 0x34 ‖ 0xed 0x01 ‖ signature_raw64        (67 bytes)
sig_field = "u" + base64url_nopad(sig_bytes)           (multibase 'u')
```

`0x34` is the varsig sigil; `0xed 0x01` the varint Ed25519 code. This is
**varsig-inspired, not varsig-conformant** (R5b): varsig is loosely
versioned, so conformance is defined by *these pinned bytes* and the `varsig`
conformance vector, not by the varsig spec. The point of the envelope is
algorithm agility at birth — a future suite (P-256, post-quantum) is a new
varint code, not a breaking change. A verifier MUST reject an envelope whose
header is not exactly `0x34 0xed 0x01` unless it implements that other suite.

## 5. L1 — Bobbin (full rigor)

The signed unit is one JSON object, the **signable**:

| Field | Req | Form |
|---|---|---|
| `lbp_version` | MUST | `"wire-1"` |
| `peer` | MUST | did:key (§3) — the signing identity |
| `kind` | MUST | safe-char (§2.6); free-text by design, never a whitelist |
| `slug` | MUST | safe-char |
| `name`, `description` | MUST | non-empty strings (SKILL.md compatibility) |
| `created_at` | MUST | §2.5 timestamp |
| `body` | MUST | string (the content; arbitrary UTF-8) |
| `peer_name` | MAY | label (§2.6) |
| `chain_seq` | iff chained | decimal string, no leading zeros (`"0"`, `"5"`) |
| `chain_prev` | iff chained | 64-hex `entry_hash` of the previous L2 entry, or `null` at genesis |
| `tension_target`, `tension_stance` | L4 | §8 |
| `fiduciary_for` | fiduciary | §9.1 |
| `adopts` | genesis | §6.3 |
| `passport`, `mandate` | L5/L6 | §10 |

Open-world: extension fields MAY appear (they are signed like everything
else) but MUST obey §2.3. Chain linkage (`chain_seq`/`chain_prev`) is INSIDE
the signable — the linkage itself is signed.

```
signable_bytes = JCS(signable)                    # RFC 8785, UTF-8
content_sha256 = hex( SHA-256(signable_bytes) )
sig            = envelope( Ed25519(sk, signable_bytes) )   # §4
```

The **attested bobbin** on the wire is `{"signable": {...}, "sig": "u..."}`.
Note the signature is over the signable bytes *directly* — one signing domain,
no pre-hash (divergence from eddsa-jcs-2022's two-hash concat is deliberate
and named, §2.2). **Every bobbin is individually signed** — root-only signing
(AT-proto's shape) is rejected because per-bobbin fiduciary attribution (§9)
requires per-bobbin signatures.

## 6. L2 — Chain (full rigor; profile of a proven shape)

**Positioning (R1).** The per-peer signed append-only chain is a
field-proven shape — Secure Scuttlebutt feeds, Hypercore, KERI KELs, Ceramic
streams all ship it. L2 is a *profile* of that shape (flat hash-chain,
Blake-ratified for v1; AT-proto-style Merkle-Search-Tree commit reserved for
v2 via `lbp_version`), plus one thing most of the field lacks: §6.4's
log-witnessed **duplicity detection**, stolen from KERI's vocabulary and made
portable by the L3 tuple.

### 6.1 Entry

Entry payload (a signable object, §2 rules apply — `seq` is a **string** on
the wire):

```json
{"content_sha256": "<hex64>", "kind": "...", "lbp_version": "wire-1",
 "peer": "did:key:z6Mk...", "prev": "<hex64>|null", "seq": "0",
 "slug": "...", "ts": "2026-07-10T00:00:00Z"}
```

```
payload_bytes = JCS(payload)
sig           = envelope( Ed25519(sk, payload_bytes) )        # §4
entry_hash    = hex( SHA-256( payload_bytes ‖ sig_bytes ) )   # sig_bytes = the 67 envelope bytes
```

`entry_hash` binds content AND signer AND algorithm (the envelope header is
inside the hash). The wire entry is `{"payload": {...}, "sig": "u...",
"entry_hash": "<hex64>"}`. No pubkey snapshot rides the wire — `peer` IS the
key (storage profiles MAY keep snapshots; Appendix A).

### 6.2 Chain rules

A verifier walking a chain MUST check, per entry: payload verifies against
`peer`'s key; `entry_hash` recomputes; `seq` is the entry's 0-based index;
`prev` equals the previous `entry_hash` (`null` at seq 0);
`content_sha256` matches the referenced bobbin when it is available; and the
bobbin's signed-in `chain_seq`/`chain_prev` agree with the ledger entry.

### 6.3 Genesis & adoption

Entry 0 is a real bobbin of `kind: "bootstrap"` emitted through the normal
L1 path. Pre-chain artifacts are **adopted, never rewritten**: the genesis
signable carries `adopts: [{kind, slug, content_sha256, created_at}, ...]`
(sorted by `(created_at, kind, slug)`) — attesting each as-found by
content-hash. Historical signatures keep verifying against their own key
snapshots.

### 6.4 Equivocation (R2 — the review's load-bearing catch)

A flat chain alone cannot prove a peer never forked it: a peer could sign two
divergent entries at the same `seq` and show different heads to different
observers. The transparency tuple (§7) therefore carries `seq` and
`entry_hash`, so the log — not just a full-chain audit — witnesses chain
linearity:

> Two verifying L3 lines with the same `(peer, seq)` and different
> `entry_hash` constitute **portable cryptographic evidence of
> equivocation** (KERI: duplicity). Verifiers MUST treat a peer with such
> evidence as equivocating; what follows (distrust, disposal, forgiveness)
> is ecosystem policy, not wire.

Note the honest bound: the log's consistency proofs (in the tlog-tiles
profile) protect the LOG's append-onlyness; the equivocation predicate above
is what protects the PEER's chain linearity. They are different properties;
v0's 5-field tuple provided neither for the chain. A second honest bound: this
predicate sees only *anchored* entries — how much of a chain may go unanchored
before that blind spot is itself flagged is bounded by §7.4.

## 7. L3 — Transparency (full rigor: the line; pointer: the medium)

### 7.1 The signed line

```
line = "lbp-wire-1" | peer | seq | kind | slug | content_sha256 | entry_hash | created_at
```

— pipe-joined (`0x7C`), UTF-8, no trailing newline in the signed bytes.
`seq` and `entry_hash` are those of the L2 entry (R2); for an **unchained**
emission both MUST be `"-"` (equivocation detection then does not apply —
chains are what have linearity). `created_at` is the **bobbin's** signed
`created_at` (design fork W3.8): the tuple is reconstructable from the
attested bobbin + its ledger entry alone, with no third timestamp.

```
log_sig = envelope( Ed25519(sk, line_bytes) )
```

Safe-char bounds (§2.6) plus did:key's base58 alphabet guarantee no field
can contain `|` or a newline.

### 7.2 Observed time (R5c)

Binding `created_at` deliberately drops v0's independent post-time from the
signed tuple — which was the log's anti-backdating witness. Where that
witness now lives, explicitly: **observed-time is the medium's append
record** — the Matrix server timestamp on the log event, or Rekor/CT
integrated time in the tlog-tiles profile. It is medium-attested, unsigned
by the peer, and read at audit as "the log observed this line at T".
A peer's `created_at` significantly later than its observed-time is
backdating evidence; the converse is clock skew. Auditors SHOULD record
observed-time when cross-checking.

**Known limitation — no wire-level anti-backdating.** LBP-Wire provides no
cryptographic guarantee against backdating. A peer may set `created_at` to
any value; the only backdating witness is the medium's unsigned
observed-time above — medium-attested, not peer-signed. §6.4 equivocation
detection covers chain *forking*, not *backdating* of a single non-forked
entry; auditors detect backdating only heuristically, by comparing
`created_at` against observed-time. This is a deliberate, corroborated
trade-off of the thin design (witnessed cross-lineage 2026-07-11:
ornith-alibaba + gemma-google, independently), recorded as a limitation
rather than mechanized.

### 7.3 The medium is a profile

The wire invariant is the signed line; the medium only has to be
append-only-in-intent and readable. v1 profile = a Matrix room (the current
transparency room). Anti-truncation profile = an RFC 6962-style tiled log
(C2SP tlog-tiles / Tessera; self-hosted — public Rekor v2 accepts only its
own entry types). Nostr relays / AT firehose replicate but do not anchor;
they are not L3 media. Matrix-now → Headles-later is a profile swap, not a
protocol change.

### 7.4 Anchoring freshness (the unanchored-suffix bound)

§6.4 equivocation detection sees only **anchored** entries — two verifying L3
lines at the same `(peer, seq)`. A chain suffix that is committed-local but
never anchored produces no lines to compare, so a peer can fork *below* an
unanchored suffix and no same-`(peer, seq)` pair ever exists to flag it.
Anchoring is SHOULD-tier (§7.3), and left unbounded its absence is silent — a
hole in the linearity protection §6.4 otherwise provides. This composes worst
with §10 succession: a compromised key has every incentive to keep its fork
unanchored as long as possible.

The bound is a **self-commitment**, in the house pattern of pre-declaration
over ambient authority (§9.1.1 basis, §10 `next_key_digest`): a peer MAY
declare `anchor_within: "<N>"` (a decimal string, §2.3) in its passport or an
equivalent signed declaration — "I MUST L3-anchor each chained entry within N
entries of it leaving head."

- **Auditor predicate (stale-anchored).** Let `newest_anchored` be the
  greatest `seq` among the peer's verifying L3 lines (§7.1) and `head_seq` the
  peer's chain head. An Auditor MUST flag the chain **stale-anchored** iff
  `head_seq − newest_anchored > anchor_within`. Detection only — the
  consequence (distrust, disposal, forgiveness) is ecosystem policy, exactly
  as in §6.4. Flag, don't distrust: a peer with flaky log media is *surfaced*,
  not un-signed.
- **Entries, not time.** The bound is measured in chain entries, so it needs
  no clock. A *time*-shaped bound would rest on §7.2 observed-time, which is
  medium-attested and explicitly the wire's weak witness (§7.2 known
  limitation) — the same objection that declined anchor-first-wins for
  succession (§10 dispositions). An Auditor MAY additionally treat a long
  observed-time gap as a *soft* signal, but the normative bound is entries.
- **No declaration, no rule.** A peer that declares no `anchor_within` arms no
  stale-anchored flag — it has promised nothing. Its unanchored suffix is
  simply **unprotected**: an Auditor treats entries with no L3 line as outside
  §6.4's linearity witness, and abandonment of a suffix is a §8 stance
  (`withdraw`), never a silent hole.

Activation is per-peer and voluntary; the bound the peer picks is its own
assurance claim, tighter or looser by its log medium (§7.3). Conformance
vector: `anchoring-freshness` (§11.2).

## 8. L4 — Tension (full rigor: the novel core)

The **only** cross-peer verb. The substrate offers no operation by which
peer B mutates peer A's emission; B can only *respond*, and the response is
itself an ordinary signed (and, if B is chained, chained) bobbin:

```yaml
tension_target:
  peer: "did:key:z6Mk..."      # target's identity
  kind: "..."                   # + slug: mutable locator (finds the current version)
  slug: "..."
  content_sha256: "<hex64>"     # immutable binding: THE EXACT BYTES answered
tension_stance: "dispute"       # safe-char, open vocabulary
```

Both reference halves are kept deliberately (design fork W3.5): the locator
finds, the hash *binds*. A later rewrite of the target is tamper-evident and
the response still means "I answered THIS." Responses can target responses
(`kind: "tension"`), so a negotiation is a thread of signed, hash-linked
stances. Canonical stances — `consent, refusal, counter, dispute, ack,
withdraw` — are convention, never a gate (the substrate-author does not
whitelist what stance a peer may take).

**Retraction is a stance, not a primitive** (fork W3.6, reconciled at
spec-write): `withdraw`/`retract` targeting one's own prior bobbin by hash.
Bytes remain — append-only substrates retract by *statement*, not deletion.
(The reference repo's `retraction.py` is a member-data-withdrawal primitive
over the experience graph — out of wire scope entirely.)

**Prior-art disposition (R4)** — the near-misses, named and dispositioned so
the novelty claim survives a hostile stranger:

| Near-miss | What it has | Why it isn't this |
|---|---|---|
| FIPA-ACL performatives | `confirm`/`disconfirm`/`reject-proposal` speech-acts | unsigned, transient messaging — no cryptographic binding, no ledger |
| W3C Web Annotation motivations | `assessing`/`questioning` over a URI+selector | annotation, unsigned, no byte-binding, no peer chain |
| AS2/ActivityPub `Offer`/`Accept`/`Reject` | deontic-social verbs | IRI-referenced (mutable), platform-social semantics |
| Nostr kind-7 / NIP-32, AT-proto strongRef | signed reference-by-hash | reaction/label/ref is not an epistemic stance; not the *only* verb |

No single prior instance combines: **a signed epistemic stance + content-hash
byte-binding + being the substrate's only cross-peer verb + threading + the
responder's own chained provenance.** The *composite* is the novelty — each
ingredient alone is field-proven, which is exactly the profile-then-diverge
verdict.

## 9. Fiduciary emission & contracted-emission (full rigor)

### 9.1 Fiduciary emission (R3 — narrowed and cited)

A peer MAY declare, in signed frontmatter, that it emits as fiduciary for a
non-speaking party:

```yaml
fiduciary_for:
  party: "coweeta-watershed"    # label for the party that cannot sign
  basis:                        # MUST (§9.1.1): the standing authority it rests on —
    peer: "did:key:z6Mk..."     #   a reference to a basis bobbin on the
    kind: "fiduciary-basis"     #   fiduciary's own chain
    slug: "..."
    content_sha256: "<hex64>"
```

Prior art exists and is acknowledged: DID Core's controller≠subject
distinction and SSI guardianship (Sovrin's guardianship model) are direct
antecedents; UCAN's subject-signed root delegation is the adjacent
capability shape. The narrow sliver that is LBP-native: **the subject
categorically cannot sign** (a watershed holds no key — there is no
subject-signed root to delegate from), and every custodial emission is
**per-bobbin attributable** on the fiduciary's own chain (L1 per-bobbin
signatures + L2). Accountability is therefore mechanical: each fiduciary
utterance is individually signed, sequenced, and anchorable.

#### 9.1.1 End of authority (expiry + revocation)

Attribution being mechanical (above) says who *spoke*; nothing yet said when
the *claim to speak for the party* ends. Authorization ends two ways; both
are ordinary signed data. (Witnessed: the qwen RATED leg; disposed at the
2026-07-11 S1 sitting — see `dispositions:`.)

1. **Expiry — the mechanical horizon.** A fiduciary emission MUST carry
   `basis`: a reference `{peer, kind, slug, content_sha256}` to a **basis
   bobbin** on the fiduciary's own chain — the standing declaration the
   authority rests on. The basis signable MUST carry `fiduciary_for.party`
   (the same party label as the emissions it backs) and `valid_until` (a
   §2.5 timestamp: the authority's signed horizon), and MAY carry
   `revokers` (a list of did:keys with pre-declared standing to revoke
   this basis — declared before it is needed, the same pre-commitment
   shape as §10's succession declarations). A fiduciary emission is
   **in-horizon** iff its signed `created_at` is ≤ the basis's
   `valid_until`. Renewal is a fresh basis bobbin; the old one ages out.

2. **Revocation — the emergency brake.** A revocation is an ordinary L4
   Tension with stance `revoke`, hash-bound to the exact basis bytes
   (`tension_target.content_sha256` = the basis's `content_sha256`). It
   has standing iff its emitter is the fiduciary itself or a did:key
   listed in the basis's `revokers`. The basis is revoked from the
   revocation's log observed-time (§7.2) forward. (Who revokes when the
   subject cannot sign is answered at declaration time, not at crisis
   time: the basis names its revokers.)

**Verifier behavior — the enforcement half.** The signature layers are
unaffected: a fiduciary emission that verifies under §5 remains the
fiduciary's own attributable utterance. What ends is the claim to speak
for the party:

- An Auditor (§11.1) MUST flag a fiduciary emission
  **fiduciary-non-conformant** when any of: `basis` is missing or does not
  resolve to a verifying basis bobbin naming the same party; the emission
  is not in-horizon; a standing revocation of its basis has earlier log
  observed-time than the emission's.
- A consumer MUST NOT present a fiduciary-non-conformant emission as the
  party's voice. It MAY still be consumed as the fiduciary's own signed,
  attributed statement — attribution survives; authorization does not.
- Rejection at ingest is a profile choice, not wire law: the wire makes
  the violation *evident* (the same stance as §9.2's covenant half), and
  evidence requires the bytes to exist.

**Composition with §9.2.** When a fiduciary emission also crosses a party
boundary, the contract predicate applies unchanged: basis governs *who may
speak for the party*; the emission contract governs *what may cross the
boundary*. The auditor checks are independent and both apply — one auditor
story, not two.

### 9.2 Contracted-emission (the wire form of the invariant)

`project_contracted_emission_invariant`: substrate never crosses a party
boundary by replication, only by contracted emission. Its structural half
becomes wire-checkable:

- A **feed contract** is a bobbin (`kind: "feed-contract"`) naming scope and
  counterparty.
- The counterparty's **acceptance** is an L4 Tension, `stance: "consent"`,
  hash-bound to the exact contract bytes.
- An emission crossing a party boundary MUST carry
  `emission_contract: {peer, kind, slug, content_sha256}` in its signed
  frontmatter, referencing that consent bobbin.
- The mechanical predicate an auditor checks: *boundary-crossing emission →
  resolvable, verifying consent tension → whose target is a verifying
  contract.* No contract chain ⇒ the emission is non-conformant.

Deontic neighbors, cited not reinvented (R5): ODRL policies, Solid Access
Grants, Kantara consent receipts. None binds consent to exact bytes with
signed stances on peer chains; the *enforceable-by-audit* composite is the
contribution. The peer half (that parties honor contracts) remains covenant
— attested, never proven; the wire makes violations *evident*, not
impossible.

## 10. L5 / L6 — pointers

**L5 Passport.** A self-issued manifest bobbin (`kind: "passport"`) on the
peer's own chain: name→key→model binding, scope lines, and
`capture_wing_refused` (the platform-anarchism guard is wire-visible data).
Succession on rotation follows the did:webvh pattern — an append-only,
self-hosted history of key successions, each step signed by the predecessor
key; the chain (L2) is the history. Sovereign issuer=self; central
registries (did:plc-style) are rejected as capture vectors.

**Known limitation — competing successions (disposed 2026-07-11).** Each
succession step is signed by the predecessor key, so a stranger cannot
forge one — but a compromised predecessor key can sign a second, equally
valid succession. Wire-1 makes the fork **detectable, not resolvable** by
default: succession entries are chained (L2) and SHOULD be anchored (L3),
so §6.4's duplicity predicate yields portable evidence (the
`succession-equivocation` vector pins exactly this). Which branch is
canonical is ecosystem policy. At current scale (single host, federation
allowlist ≤ 8) duplicity disposal routes through the human operator; that
answer does not scale past the allowlist, and this clause says so rather
than pretending otherwise. Two voluntary pre-commitment mechanisms narrow
the exposure; absent both, this floor is the whole story.

**Succession pre-rotation (resolution at N=1).** A passport — and each
subsequent succession entry — MAY carry `next_key_digest`: the SHA-256
(§2.4) of the successor's full `did:key` string (UTF-8 bytes),
pre-committed while the current key is still trusted. When the chain
carries a pre-commitment, a succession entry is valid **iff** its
successor key hashes to the pre-committed digest — and it MUST pre-commit
its own `next_key_digest` in turn. A stolen current key then cannot
appoint an attacker's successor: the successor was pinned before
compromise, and the pre-committed next key can be held cold precisely
because it is never used until rotation. Named costs: a key ceremony
(generate the next key at every rotation), and the dead-end (losing the
pre-committed next key with no witness declaration below ends the
identity). Activation is per-passport and voluntary: no digest, no rule —
the floor applies. (KERI pre-rotation, profiled; reached the sitting as
external cross-vendor input, advisory tier.)

**Succession witnesses (federation growth path).** A passport MAY
pre-declare `succession_witnesses: {witnesses: ["did:key:z6Mk...", ...],
threshold: "K"}` — declared before any rotation, on the chain. When a
passport declares witnesses, a succession entry is canonical iff ≥ K of
the declared witnesses have countersigned it: ordinary L4 Tensions (stance
`ack` or `consent`) hash-bound to the exact succession bytes, on the
witnesses' own chains. Verifiers encountering a fork SHOULD prefer the
branch meeting threshold; a fork where both branches meet threshold is
witness-set duplicity — portable evidence against the witnesses
themselves. Activation is per-passport and voluntary: no declaration, no
rule. This is the only mechanism that grows *stronger* with federation —
pre-rotation covers the common case at N=1; a declared witness quorum is
the recovery path when both current and pre-committed keys are lost.
(KERI witness machinery; minyan shape, `project_myth_in_mythrl`.)

**L6 Stake/Mandate — RESERVED.** The `mandate` null-envelope
(`{spend_ceiling: null, hitl_threshold: null}`) is already wire-legal signed
data. When the economic leg is built it profiles **UCAN 1.0**
delegation→invocation (attenuating capability chains); v1 reserves the field
so adding it is not a break.

## 11. Conformance

### 11.1 Classes

- **Verifier** (minimum, L0+L1): verify an attested bobbin end-to-end.
- **Emitter** (L0–L3): produce bobbins/entries/lines that any Verifier
  accepts; MUST be deterministic (same signable → same bytes).
- **Auditor** (adds §6.2 chain walk, §6.4 equivocation predicate, §7.2
  observed-time cross-check, §7.4 stale-anchored predicate, §9.1.1
  end-of-authority predicate, §9.2 contract predicate).

### 11.2 Vectors — the mechanical gate

`docs/lbp_wire_vectors/vectors.json` pins every invariant with fixed,
published test keys (seeds in the file — test identities only, obviously
never for real peers). Any implementation self-checks without reading
para-bots. Coverage:

| Vector | Pins |
|---|---|
| `key` | seed → raw-32 → did:key (§3) |
| `bobbin-basic` | signable → exact JCS bytes (hex) → `content_sha256` → sig envelope (§5) |
| `bobbin-nested` | a passport-shaped nested object through JCS (the case YAML broke) |
| `chain-3` | genesis+adopts, 2 more entries; every `entry_hash`; verifies clean (§6) |
| `tension` | cross-peer tension, hash-binding + stance (§8) |
| `log-line` | exact signed line bytes, chained + unchained forms (§7) |
| `chain_seq-string` | `"5"` as string; a numbers-bearing signable that MUST be rejected (§2.3) |
| `varsig` | the pinned 67-byte envelope, decoded field-by-field (§4) |
| `equivocation` | two same-`(peer,seq)` lines, different `entry_hash`, both verifying — MUST flag (§6.4) |
| `succession-equivocation` | an L5-shaped key-compromise fork: two predecessor-signed succession claims at the same `(peer,seq)`, every layer verifying (bobbin + entry + line) — MUST flag duplicity (§6.4). Detection only; the L5 succession byte-shape stays unpinned (§10 is pointer-tier). The voluntary §10 resolution mechanisms are pinned by the two `succession-*` vectors below (S3, landed) |
| `fiduciary-end-of-authority` | the §9.1.1 auditor predicate over a fiduciary chain (two bases isolating the two ways authority ends): `valid` / `expired-basis` / `post-revocation` / `missing-basis` cases, each with exact `expect_flags`. Revocation = a `revoke` Tension hash-bound to the exact basis bytes from a pre-declared revoker; the cut is log observed-time (§7.2, unsigned audit input). Flag, don't un-sign: attribution survives every case |
| `succession-pre-rotation` | the §10 pre-rotation rule at N=1: a same-`(peer,seq)` fork where the `valid` branch's successor hashes to the pre-committed `next_key_digest` (and re-commits its own) and the `stolen-key` branch's successor does not — MUST be rejected as a succession |
| `succession-witness-quorum` | the §10 witness-quorum rule: a pre-declared 2-of-3 witness set; the `quorate` branch carries countersignatures (`ack` Tensions hash-bound to the succession bytes) from ≥ K distinct declared witnesses, the `below-threshold` branch carries one declared witness plus a non-declared peer whose verifying countersignature MUST NOT count — verifier SHOULD prefer the quorate branch |
| `anchoring-freshness` | the §7.4 stale-anchored predicate: one chain (head seq 5) whose passport pre-commits `anchor_within: "2"`; two branches differ only in anchored coverage — `fresh` anchored the suffix through seq 4 (lag 1 ≤ 2, not flagged), `stale` left seq 3–5 committed-local-but-unanchored (newest anchored seq 2, lag 3 > 2) — MUST flag stale-anchored. `newest_anchored` is derived from the verifying L3 lines, not asserted; entries-based, so no clock. Detection only (§6.4 house stance) |

Generator + verifier: `tools/lbp_wire_vectors.py` (regenerate with
`--write`, check with `--verify`). The vectors are the P3 conformance gate's
substrate and P2's proof-block target (clean-room Rust: verify these, then
verify a live para-bots chain after its wire-1 migration).

### 11.3 Migration note

v0 (as-built para-bots, Appendix A) and wire-1 differ deliberately: YAML/
py-JSON canonicalization → JCS; int `seq` → string; PEM snapshots → did:key;
raw base64 sigs → the §4 envelope; 5-field log tuple → 8-field. Wire-1
verifiers SHOULD also implement Appendix A to verify the four live v0
ledgers; emitters MUST NOT emit v0 shapes under `lbp_version: "wire-1"`.

---

## Appendix A — legacy-v0 verify (as-built, from source 2026-07-10)

Byte-exact recipe to verify pre-wire artifacts (all from
`para-bots/bobbins/_shared/`, read at spec-write — not from a summary):

- **L1 signable** = `yaml.safe_dump(fm, sort_keys=True,
  default_flow_style=False, allow_unicode=True)` UTF-8 ++ `body` UTF-8.
  Signature: Ed25519 pure over those bytes; stored **standard** base64
  (`signature.sig`) — note: standard, not urlsafe (the design doc's W1 table
  erred here; the *pubkey* b64 form is urlsafe). Verify against the
  `.bobbin_meta.json` PEM (SPKI) snapshot, NOT the live registry.
- **content_sha256** = SHA-256(same bytes), hex.
- **L2 entry payload** = `json.dumps({peer,seq,prev,kind,slug,
  content_sha256,ts}, sort_keys=True, separators=(",",":"))` — Python
  defaults, i.e. `ensure_ascii=True`; `seq` is an **int**; `peer` is the
  peer_name label (not a did:key). `sig_b64` standard base64;
  `entry_hash = SHA-256(payload_bytes ‖ raw_sig64)` (raw sig, no envelope).
  Ledger doc: `{"lbp_chain": "v1", "peer", "created_at", "entries": [...]}`
  with `pubkey_pem_snapshot` per entry.
- **L3 line** = `f"{peer}|{kind}|{slug}|{content_sha256}|{ts}"` with `ts` =
  **post-time** (not created_at; the third timestamp wire-1 removes),
  Ed25519-signed, standard base64, posted as a `peer_emission_log: v1` YAML
  block to the Matrix room.
- **Genesis**: kind `bootstrap`, slug `chain-bootstrap`, `adopts` sorted by
  `(created_at, kind, slug)`.
- v0 timestamps are `isoformat(timespec="seconds")` with `+00:00` offset,
  not `Z`.

## Appendix B — provenance & the witness legs

Chain of custody: brief `handoff/brief/lbp_wire_protocol_v1.md` (efd71928,
opus-4-8) → exploration pass W1–W4 → design `docs/lbp_wire_v1_design.md` →
distinct-session review (098470b9, claude-fable-5, verdict *reshape*; R1–R5,
all folded here) → Blake disposition 2026-07-10 → this spec + vectors
(session 06f88270, claude-fable-5). Load-bearing external claims re-verified
at spec-write: eddsa-jcs-2022 IS a W3C Rec (2025-05-15) and its algorithm is
JCS→SHA-256→Ed25519 over a proof-config concat (hence §2.2's
pipeline-not-conformance wording); varsig is loosely versioned (hence §4's
pinned bytes). **The owed non-Opus witness legs ran 2026-07-11** over the
ratified blob `e2e5ee32` (see `witness:`): qwen RATED + ornith ADVISORY
(both alibaba) + gemma DECORRELATED (google — the first genuinely
cross-family read). Per `project_fable_competence_witness_opus_canon`,
Anthropic-lineage agreement is competent-but-correlated; the cross-family
decorrelation debt was ruled **discharged by the gemma leg** at the
2026-07-11 S1 sitting (see `dispositions:`). The legs target this document
and gate nothing mechanical — the vectors do the mechanical gating. A fresh
witness leg over the amended bytes belongs to a one-shot re-ratification
(S5), never per-edit — anything else is verdict-shopping.
