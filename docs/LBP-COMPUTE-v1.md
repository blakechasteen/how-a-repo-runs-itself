# LBP-Compute v1 — metered compute as a contracted-emission profile

```
status:      DRAFT-1 (profile of LBP-Wire v1 — NOT a protocol revision)
gate:        the parent spec's cross-family (qwen) witness leg is still OWED
             (the P2 witness record def4f207 is fable-verifying-fable and does
             not discharge it). This profile inherits that gate: treat as
             draft until the parent's decorrelation leg lands.
lineage:     design conversation Blake ↔ session 4a786860 (2026-07-10/11) →
             handoff/brief/lbp_compute_receipts_profile.md → this document
             (same session, Blake-directed pickup).
parent:      docs/LBP-WIRE-v1.md — all §-references below are to it unless
             marked (this doc). Common wire rules (§2), identity (§3),
             signatures (§4), bobbin (§5), chain (§6), transparency (§7),
             tension (§8), contracted-emission (§9.2) apply UNCHANGED.
vectors:     docs/lbp_compute_vectors/vectors.json (generated + verified by
             tools/lbp_compute_vectors.py — see C13)
```

**What this is.** The profile two LBP-Wire peers need to sell and buy
metered compute with co-signed, auditable receipts: a provider (data center,
GPU rig) and a buyer (human org or AI peer). It adds **zero wire changes**:
four coined kinds, two signed extension-field blocks, and one pinned Merkle
construction. Kinds are free-text by design (§5); extension fields are
open-world and signed (§5); the contract mechanism is §9.2's
contracted-emission predicate with a sibling contract kind. The product this
profile enables is **verifiable compute receipts** — who ran what, on which
attested hardware, for how long, co-signed by both parties, anchored
publicly — independent of any marketplace existing.

Keywords MUST / MUST NOT / SHOULD / MAY per RFC 2119. Section numbers in
this doc are prefixed **C** to avoid colliding with parent §s.

---

## C1. Roles & conformance asymmetry

- The **provider** — the party whose metering honesty is in question — MUST
  be a conformant Emitter (parent §11.1: L0–L3 — chained, logged). All
  billing-bearing emissions (consent, receipts, invoices) ride the
  provider's chain and are anchored as L3 lines.
- The **buyer** MAY be a Verifier only (L0+L1). An unchained buyer's
  contract proposals, acks, and disputes still bind — L4 does not require
  the responder to be chained. A buyer who wants its own portable dispute
  history SHOULD run a chain, but the meter's auditability never depends on
  it.

## C2. Kinds and lifecycle

| Step | Wire form | This doc |
|---|---|---|
| Offer / RFQ | `kind: "compute-offer"` bobbin — optional discovery; no protocol role | C4 |
| Contract | `kind: "compute-contract"` bobbin + `compute_terms` block | C4 |
| Negotiation | tension thread: `counter` stances targeting prior contract bytes (§8) | C5 |
| Acceptance | tension `stance: "consent"` hash-bound to exact contract bytes (§9.2) | C5 |
| Job submission | `kind: "compute-job"` manifest — private contracted emission, never logged | C6 |
| Metering | `kind: "compute-microreceipt"` (unchained) rolled into `kind: "compute-receipt"` per epoch (chained) | C7 |
| Usage commitment | `usage_root` — pinned RFC 6962-style Merkle root | C8 |
| Co-signature | buyer tension `stance: "ack"` hash-bound to receipt bytes | C9 |
| Dispute | buyer tension `stance: "dispute"` targeting the exact receipt | C9 |
| Invoice | `kind: "compute-invoice"` over an epoch range; buyer consent = agreement to pay | C10 |

Both flow directions ride ONE §9.2 predicate: the workload crossing *into*
the provider and the receipts crossing *back* to the buyer are both
boundary-crossing emissions carrying `emission_contract` referencing the
same consent bobbin (C5).

## C3. Money on the wire

Parent §2.3 (no JSON numbers; all numerics as decimal strings) applies to
every field in this profile. The consequence is deliberate and load-bearing:
**amounts, prices, and usage counts are exact decimal strings**, so the
IEEE-754 rounding class of billing bug is structurally unrepresentable.
Verifiers MUST compare monetary and usage quantities by **numeric decimal
equality** (e.g. `"0"` equals `"0.000000"`), never by string equality, and
MUST perform arithmetic checks (C11) in exact decimal arithmetic.

## C4. `compute-contract`

An ordinary L1 bobbin. The `body` carries the legally operative
human-readable terms; the signed `compute_terms` extension block carries the
machine-checkable subset. Both are inside the signable — one signature
covers both. Either party MAY propose.

```json
{
  "lbp_version": "wire-1",
  "peer": "did:key:z6Mk...proposer",
  "kind": "compute-contract",
  "slug": "cc-<engagement>-<yyyymm>",
  "name": "...", "description": "...", "created_at": "...",
  "body": "<human-readable contract prose>",
  "compute_terms": {
    "provider": "did:key:z6Mk...",
    "buyer": "did:key:z6Mk...",
    "resource": {"class": "gpu", "sku": "h100-sxm-80g", "count": "8",
                 "attestation": "nvidia-cc", "region": "us-east"},
    "pricing": {"unit": "gpu_second", "unit_price": "0.000833",
                "currency": "USD"},
    "epoch": "PT1H",
    "valid_from": "2026-08-01T00:00:00Z",
    "valid_until": "2026-09-01T00:00:00Z",
    "audit": {"micro_receipts": "on-demand", "retention": "P90D"},
    "sla": {"availability": "0.99", "remedy": "credit"},
    "data_terms": "no-retention"
  }
}
```

Field rules:

- `compute_terms.provider` / `.buyer` MUST be did:keys; one of them MUST
  equal the signable's `peer` (the proposer names itself).
- `pricing.unit` names the metered quantity; `usage.<unit>s` in receipts
  (C7) MUST carry that quantity. `unit_price` and all quantities are
  decimal strings (C3).
- `epoch` is an ISO 8601 duration. Together with `valid_from`, it fixes the
  receipt cadence and makes the expected epoch count computable (C7's
  completeness property).
- `resource.attestation` names the hardware-attestation scheme
  (`"none"` MUST be stated explicitly rather than omitted).
- Extension keys beyond these MAY appear (open-world, §5).
- **Slug discipline (operational MUST):** slugs appear in public L3 lines —
  they MUST NOT contain counterparty-identifying names beyond what the
  parties accept as public.

## C5. Formation — consent, counters, and the round trip

Formation is §9.2 verbatim with `compute-contract` as a sibling of
`feed-contract` (the parent's predicate never depends on the kind name):

1. Proposer emits the `compute-contract` bobbin. Its signature binds the
   proposer to those exact bytes.
2. The counterparty accepts with an L4 tension, `stance: "consent"`,
   `tension_target.content_sha256` = the contract's exact bytes. A
   chained counterparty SHOULD chain the consent. Together the two
   signatures are the bilateral agreement — resolving the consent yields
   both parties' assent (consent sig → target contract sig).
3. A counter-offer is a NEW `compute-contract` bobbin plus a tension
   `stance: "counter"` targeting the prior version's bytes. The thread is
   the negotiation record.
4. Every subsequent boundary-crossing emission under the engagement — job
   manifests inbound, receipts/invoices outbound — MUST carry
   `emission_contract: {peer, kind, slug, content_sha256}` referencing the
   **completing consent tension** (whichever party emitted it). One
   pointer, bilateral proof.

## C6. Jobs — private by construction

A job manifest is a `kind: "compute-job"` bobbin: the workload reference
(image/digest, command, input hashes), signed by the buyer, carried
provider-ward as a **private contracted emission**. It MUST carry
`emission_contract` (C5.4). It MUST NOT be posted to L3 and SHOULD NOT be
chained by the buyer unless the buyer wants its job history public —
workload privacy is the default. Receipts bind jobs by hash only
(`job_sha256`, C7): the public record proves *that* a specific job ran,
never *what* it was.

## C7. Receipts — micro (unchained) and epoch (chained)

### C7.1 `compute-microreceipt` — one per job, unchained

An ordinary unchained L1 bobbin the provider signs and **retains**; produced
to the buyer/auditor on demand under `compute_terms.audit`. Never chained,
never logged — its `content_sha256` is the Merkle leaf (C8).

```json
{
  "lbp_version": "wire-1",
  "peer": "did:key:z6Mk...provider",
  "kind": "compute-microreceipt",
  "slug": "mr-<engagement>-e<epoch>-j<n>",
  "name": "...", "description": "...", "created_at": "...",
  "body": "",
  "micro": {
    "contract_sha256": "<hex64>",
    "epoch_seq": "0",
    "job_sha256": "<hex64 — content_sha256 of the compute-job manifest>",
    "started": "2026-08-01T00:03:11Z",
    "ended": "2026-08-01T01:03:11Z",
    "usage": {"gpu_seconds": "3600"}
  }
}
```

### C7.2 `compute-receipt` — one per epoch, chained

```json
{
  "lbp_version": "wire-1",
  "peer": "did:key:z6Mk...provider",
  "kind": "compute-receipt",
  "slug": "cr-<engagement>-e<epoch>",
  "chain_seq": "...", "chain_prev": "...",
  "name": "...", "description": "...", "created_at": "...",
  "body": "",
  "emission_contract": {"peer": "did:key:z6Mk...", "kind": "tension",
                        "slug": "...", "content_sha256": "<consent hash>"},
  "receipt": {
    "contract_sha256": "<hex64 — the exact contract bytes consented to>",
    "epoch_seq": "0",
    "window": {"from": "2026-08-01T00:00:00Z", "to": "2026-08-01T01:00:00Z"},
    "usage": {"gpu_seconds": "12600", "jobs": "3"},
    "amount": {"value": "10.4958", "currency": "USD"},
    "usage_root": "<hex64 — C8 Merkle root over this epoch's micro-receipts>",
    "attestation_sha256": "<hex64 — this epoch's hardware quote, or absent when attestation is \"none\">"
  }
}
```

### C7.3 Completeness rules (what makes withholding evident)

- `epoch_seq` MUST start at `"0"` and increase by exactly 1 per receipt
  under one contract. Chain `seq` gives global ordering; `epoch_seq` gives
  **per-contract completeness** — a gap is evidence of a suppressed
  receipt, not silence.
- Epoch windows MUST tile `[valid_from, valid_until)` in `epoch`-sized
  steps: `window.from` of epoch N = `valid_from + N × epoch`, no gaps, no
  overlaps.
- **Idle epochs MUST still emit a receipt** (zero usage, empty
  `usage_root` — C8): the receipt stream is a heartbeat; silence is never
  legitimate inside the contract window.
- `usage.jobs` MUST equal the count of that epoch's micro-receipts, and
  every other `usage` quantity MUST equal the exact decimal sum of the
  micro-receipts' corresponding fields.
- `amount.value` MUST equal `usage.<pricing.unit>s × pricing.unit_price`
  in exact decimal arithmetic (numeric equality, C3).

## C8. `usage_root` — the pinned Merkle profile (full rigor)

The one genuinely new mechanical construct in this profile — pinned here so
independent implementations agree byte-for-byte, following the parent's
reimplement-nothing rule: this is RFC 6962 §2.1's Merkle Tree Hash, profiled.

- **Leaf input** `d(i)`: the **raw 32 bytes** (hex-decoded
  `content_sha256`) of a micro-receipt signable. The tree commits to the
  *set* of micro-receipts by content hash; each micro-receipt's own L1
  signature is verified separately on production. (Design fork, resolved:
  hashing the signable bytes into leaves was rejected — it would force the
  full bodies into every root recomputation; hash-of-hash composes with L1.)
- **Ordering**: leaves sorted ascending by raw-32 byte order. The root is a
  set commitment; chronology lives in the micro-receipts' own timestamps
  and the epoch window. Duplicate leaves MUST be rejected.
- **Hashing** (RFC 6962 §2.1, SHA-256):
  - `MTH({}) = SHA-256("")` — the **empty root** (idle epochs, C7.3):
    `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  - `MTH({d0}) = SHA-256(0x00 ‖ d0)`
  - `MTH(D[n]) = SHA-256(0x01 ‖ MTH(D[0:k]) ‖ MTH(D[k:n]))`, where `k` is
    the largest power of two `< n`.
  The `0x00`/`0x01` domain prefixes are load-bearing (second-preimage
  safety); implementations MUST NOT omit them.
- **Inclusion proof**: the RFC 6962 §2.1.1 audit path, carried as an
  ordered list of `{"dir": "left"|"right", "hash": "<hex64>"}` steps from
  leaf to root (`dir` = which side the *sibling* hash joins on). A verifier
  recomputes: start at the leaf hash; per step, `H(0x01 ‖ sib ‖ acc)` when
  `dir` is `"left"`, `H(0x01 ‖ acc ‖ sib)` when `"right"`; the result MUST
  equal `usage_root`.

## C9. Co-signature, disputes, and equivocation

The co-signature is the **tension mesh, not a shared ledger** — wire-1 has
no multi-writer chain and needs none:

- **Ack**: the buyer responds to a receipt with tension `stance: "ack"`
  hash-bound to the receipt's exact bytes. Provider signature on the
  receipt + buyer ack = bilateral attestation of that epoch's metering.
- **Dispute**: `stance: "dispute"` targeting the receipt's bytes, with the
  objection in `body` (and MAY carry structured extension fields). "I
  dispute THIS" survives any later rewrite (§8 locator/binding split).
- **Deemed acceptance** ("unacked after 72h = accepted") is contract
  policy, NOT wire. The wire records which receipts carry acks; policy
  interprets silence.
- **Equivocation = double-billing evidence.** A provider showing the buyer
  one usage figure and its own books another is exactly parent §6.4's
  predicate: two verifying L3 lines, same `(peer, seq)`, different
  `entry_hash` — portable cryptographic evidence, already vector-covered
  by the parent. Auditors MUST apply §6.4 across the receipt stream.

## C10. Invoice and the settlement boundary

`kind: "compute-invoice"`, chained on the provider, carrying
`emission_contract` plus an `invoice` block: the epoch range
(`from_epoch`/`to_epoch` — MUST be contiguous and fully receipt-covered),
total `amount` (MUST equal the decimal sum of the covered receipts'
amounts), and MAY carry `settlement_ref` (a hash-pointer into the fiat
processor's record). Buyer consent tension on the invoice = **agreement to
pay**. Settlement itself — money moving — is off-wire, deliberately.

**L6 named, not built.** A buyer *agent* operating under a UCAN-shaped
`mandate` (`spend_ceiling`, `hitl_threshold` — parent §10's reserved
null-envelope) is the natural authorizer of invoice-consents. This profile
gives L6 its first concrete production job and builds none of it.

## C11. Auditor predicate (extends parent §11.1 Auditor)

Every check is mechanical. Given a contract, its consent, and the receipt
stream:

1. §9.2 base: each boundary-crossing emission's `emission_contract`
   resolves to a verifying consent tension whose target is a verifying
   contract; `receipt.contract_sha256` matches that contract.
2. Chain + log: parent §6.2 walk and §6.4 equivocation predicate over the
   provider's chain and lines.
3. Arithmetic (exact decimal, C3): per-epoch `amount = usage × unit_price`;
   invoice total = Σ covered receipts.
4. Completeness (C7.3): `epoch_seq` contiguous from `"0"`; windows tile
   `[valid_from, valid_until)`; idle epochs present.
5. Aggregation: epoch `usage` = decimal sums over produced micro-receipts;
   `usage.jobs` = micro count.
6. Sampling: requested micro-receipts verify as L1 bobbins and prove into
   `usage_root` via C8 inclusion proofs.

## C12. Honestly outside the wire

Same covenant split as parent §9.2 — the wire makes violations *evident*,
not impossible:

- **Verification of work** — the hard problem, named: chains prove who
  claimed what, when, bound to which bytes, co-signed by whom. Whether the
  H100 was really an H100 comes from the attestation quote
  (`attestation_sha256` carries it by hash; verification of the quote is
  scheme-specific and off-wire) or replication spot-checks. Evidence
  plane, not oracle.
- **Settlement** (C10) and **remedy enforcement** (SLA credits, contract
  law, ecosystem governance).
- **Deemed-acceptance windows** (C9).

## C13. Conformance vectors

`docs/lbp_compute_vectors/vectors.json`, generated + verified by
`tools/lbp_compute_vectors.py` (same fixed published test seeds as the
parent — test identities only). Coverage:

| Vector | Pins |
|---|---|
| `usage-root-empty` | the empty root (C8) |
| `usage-root-1` | single-leaf MTH |
| `usage-root-3` | 3 leaves (unbalanced split) + an inclusion proof per leaf |
| `contract` | full `compute-contract` signable → JCS bytes → hash → sig |
| `consent` | provider consent tension, hash-bound to the contract (C5) |
| `micro-receipts` | 3 unchained micro-receipt bobbins (the leaves) |
| `receipt-epoch-0` | busy epoch: sums, exact-decimal amount, usage_root |
| `receipt-epoch-1-idle` | idle epoch: zero usage, empty root (C7.3) |
| `provider-chain` | genesis + consent + 2 receipts as a verifying L2 chain |
| `ack` | buyer ack tension hash-bound to receipt-epoch-0 |
| `must-flag-amount` | receipt whose amount ≠ usage × price — auditor MUST flag |
| `must-flag-epoch-gap` | epoch_seq 0 → 2 — auditor MUST flag withholding |

## Appendix — provenance

Brief: `handoff/brief/lbp_compute_receipts_profile.md` (sid8 4a786860,
interpreted_by claude-fable-5, Blake-directed woosh 2026-07-11; picked up
same session at Blake's direction). Parent spec read end-to-end at
profile-write. The market/economics rationale (why receipts are the wedge,
not a marketplace; the AI-peer exit-ramp argument) lives in the brief, not
here — this document is the mechanical profile only.
