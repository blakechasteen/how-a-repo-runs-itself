# LBP-Wire v1 — design (exploration-pass output)

> **Status: SUPERSEDED-BY-SPEC 2026-07-10.** Distinct-session review landed
> (098470b9, claude-fable-5, verdict **reshape** — headline confirmed, five
> reshapes R1–R5; attestation on `handoff/brief/lbp_wire_protocol_v1.md`),
> Blake dispositioned ratify-to-build ("LBP-Wire v1 review + spec-write",
> 2026-07-10), and session 06f88270 wrote **`docs/LBP-WIRE-v1.md`** + generated
> the conformance vectors (`docs/lbp_wire_vectors/`, dual-path verified).
> R1–R5 are folded into the spec, NOT retrofitted here — read the spec as
> current; this doc remains the exploration-pass record. The standing non-Opus
> (qwen) witness leg now targets the spec.
> _Historical status line:_ W1–W4 complete; three scope calls Blake-ratified 2026-07-10 (flat · Varsig-now · thin).
> Produced by the exploration pass (session `efd71928`, claude-opus-4-8, 2026-07-09/10).
> This is the pass's DESIGN output, NOT yet a ratified spec — the ratified step is
> writing `LBP-WIRE-v1.md` + generating the conformance vectors. Prior-art (W2) is
> **agent-web-sourced** (four independent subagents); the load-bearing
> `eddsa-jcs-2022`-is-a-W3C-Rec claim is re-checkable at the linked source and must
> be re-verified at spec-write.

---

## Verdict (the one that matters)

**Profile heavily, then diverge precisely.** Not bespoke; not "just adopt Nostr."
The exploration is convergent across the reference-impl archaeology (W1) and four
independent prior-art surveys (W2):

- **~60% of LBP-Wire is a *profile* of existing, shipping standards** — `did:key`
  (L0), `eddsa-jcs-2022` (L1/L5 signing), UCAN delegation (L6), RFC-6962/tlog-tiles
  (L3 structures), Nostr/AT-proto content-hash references (L4 mechanism).
- **~25% is *additive-but-standard-based*** — the per-peer hash-chain (L2) and the
  self-hosted transparency anchor (L3 deployment).
- **~15% is genuinely novel and worth a spec of its own** — **L4 Tension as an
  epistemic stance-verb** ("I dispute *these exact bytes*"), **fiduciary identity**
  (a peer as key-holder *for a non-speaking party*), and **contracted-emission
  across party boundaries**. No surveyed protocol has any of these.

**Blake's answer #2 (JCS / option B) is vindicated on evidence, not taste:** JCS is
already a W3C Recommendation cryptosuite — `eddsa-jcs-2022` (JCS/RFC-8785 → SHA-256
→ Ed25519/RFC-8032-pure) — which is LBP's L1 signing strawman *verbatim*. It also
won a head-to-head vs binary (COSE/dCBOR) on the only axis that matters for v1:
Python↔Rust byte-agreement today, with mature dual-language tooling shipping now.

This is the ideal outcome for "a stranger can implement it": they reuse existing
libraries for the ~60%, and the novel ~15% is small enough to specify tightly.

---

## W1 — as-built wire behavior (reference-impl archaeology)

Read from source: `para-bots/bobbins/_shared/{peer_owned_bobbin,peer_identity,peer_emission_log,chain,tension,peer_passport}.py`.

| Layer | What actually gets signed (as-built) | Interop note |
|---|---|---|
| **L0 identity** | Ed25519 / RFC-8032 pure (`eddsa.new(key,"rfc8032")`), raw-64 sig. Keys **snapshot as PEM** (SPKI-DER); `verify()` requires PEM. Three key forms coexist (PEM, base64url-nopad, hex). | PEM is a Python-ism; wire needs a single canonical raw-32 encoding. |
| **L1 bobbin** | `yaml.safe_dump(fm, sort_keys=True, allow_unicode=True)`·utf8 **++** `body`·utf8; `content_sha256` = sha256 of the *same bytes*. | **The trap.** Signing over PyYAML's emitter (80-col line-fold, quoting heuristics, nested-dict rendering) — not cross-language reproducible. |
| **L2 chain** | `json.dumps(payload, sort_keys=True, separators=(",",":"))`·utf8 over `{peer,seq,prev,kind,slug,content_sha256,ts}`; `entry_hash = sha256(payload_bytes ++ raw_sig)`. | **Already compact-sorted-JSON** — two-thirds of a JCS migration, but Python `json.dumps` (`ensure_ascii=True`), not RFC-8785. |
| **L3 transparency** | `f"{peer}\|{kind}\|{slug}\|{content_sha256}\|{ts}"` Ed25519-signed; posted as a `peer_emission_log: v1` YAML block to a Matrix room. | Cleanest layer; pipe-join is trivially portable. |
| **L4 tension** | `tension_target={peer,kind,slug,content_sha256}` + `tension_stance` in signed frontmatter. Reference = mutable locator **+** immutable content-hash. | The novel core, exactly as strawman. |
| **L5 passport** | nested `passport` manifest dict in frontmatter; pubkey embedded as hex (fence-safe). Carries `mandate:{spend_ceiling:null, hitl_threshold:null}` + `capture_wing_refused:[on-chain-registry, soulbound-token, dns-txt-root-of-trust]`. | Deeply-nested → worst case for the YAML trap. L6 already exists as a null-envelope; platform-anarchism guard is already in the data model. |

**Five refinements W1 forces onto the strawman:**
1. **The impl already has *two* canonicalizations** — YAML (L1) and Python-JSON
   (L2), *neither* RFC-8785. The wire spec **unifies both onto JCS**; the L2 ledger
   is an unnamed two-thirds-done JCS migration.
2. `entry_hash = sha256(payload ++ sig)` binds content *and* signer, `prev` inside
   the signed payload — stronger than the strawman's phrasing. Keep verbatim.
3. **Three independent timestamps** (bobbin `created_at` ≠ ledger `ts` ≠ log `ts`),
   so the L3 tuple is not reconstructable from the bobbin alone → a W3 fork.
4. **L6 is already half-real** (the `mandate` null-envelope); `capture_wing_refused`
   is wire-visible → directly constrains the DID/blockchain adoption question.
5. `kind`/`slug`/`stance` are **regex-bounded**, not truly free-text → a W3 fork.

---

## W2 — prior-art positioning (four independent web-grounded surveys)

Per-layer verdict (adopt = use off-the-shelf · profile = adopt shape, tighten ·
adapt = steal ideas · diverge = LBP-native):

| Layer | Verdict | Source standard | The one reason |
|---|---|---|---|
| **L0 Identity** | **ADOPT** | **`did:key`** (Ed25519 = `did:key:z6Mk…`, multibase/multicodec) | Key-*is*-identity, registry-free — exact axiom match. Keep Ed25519 (not Nostr's secp256k1). Its no-rotation limit is a *feature boundary* handed to L5. |
| **L1 Bobbin signing** | **ADOPT (alg) + PROFILE (envelope)** | **`eddsa-jcs-2022`** (W3C Data Integrity EdDSA Cryptosuites, Rec 2025-05-15) | JCS→SHA-256→Ed25519 is the strawman *verbatim*; reinventing a canonicalize→hash→sign suite when a W3C Rec matches is pure risk. Shed the JSON-LD `@context`/`DataIntegrityProof` weight. **Sign every bobbin** (diverge from AT-proto, which signs only the aggregate root — inadequate for fiduciary attribution). |
| **L2 Chain** | **DIVERGE (v1 flat) · steal MST for v2** | git-style hash-chain; **AT-proto signed-commit-over-MST** | No surveyed protocol offers a per-peer hash-chain; it's genuine LBP work. v1 = flat hash-chain (current impl, weekend-implementable). v2 optimization = AT-proto's signed-commit-over-Merkle-root (compact inclusion proofs + deterministic sync via MST unicity). **[FORK — see W3]** |
| **L3 Transparency** | **ADOPT structures · self-host instance** | **RFC-6962 / Rekor v2 tile-backed (`tlog-tiles`/Tessera)** | Merkle tree + signed checkpoint + inclusion (anti-omission) + consistency (anti-truncation) proofs — the canonical L3 model. Relays/firehose (Nostr/AT) replicate, they do **not** anchor. Public Rekor v2 accepts only `hashedrekord`/`dsse` → self-host the identical tile-backed log. |
| **L4 Tension** | **DIVERGE (core novelty) · steal the ref** | Nostr `e`-tag / AT-proto `strongRef{uri,cid}` for byte-binding | Byte-binding-by-content-hash is field-proven (steal it, validates `content_sha256`). But **no protocol has stance-as-epistemic-verb** — reactions are thin, capabilities are deontic (may-do), refs are dumb. "I dispute these exact bytes" + only-cross-peer-verb + fiduciary is LBP-native. |
| **L5 Passport** | **ADAPT** | self-issued VC envelope + **`did:webvh`** append-only key-succession history-log | did:key can't rotate; VC gives the envelope but not succession. Borrow did:webvh's verifiable history-log pattern for name→key→model persistence. Reject central directories (`did:plc`). The current chained-passport *is* this. |
| **L6 Stake/Mandate** | **ADOPT/PROFILE** | **UCAN 1.0** delegation→invocation (`sub`/`cmd`/`pol` attenuation) | Delegated economic capability is exactly UCAN's attenuating capability chain — battle-tested; profile it rather than invent. The current `mandate` null-envelope maps onto UCAN. |

**Cross-cutting steal — signature agility (from UCAN Varsig):** wrap the signature
in a **self-describing envelope** (alg marker in-band) so v1 = Ed25519 but secp256k1
/ P-256 / post-quantum are a non-breaking addition. Resolves the "signature agility"
fork cleanly.

---

## Resolved decisions (carried into the eventual spec)

1. **Canonicalization = JCS (RFC-8785), realized as `eddsa-jcs-2022`.** Confirmed
   over COSE/dCBOR for v1 (least spec surface × mature Python `rfc8785` + Rust
   `serde_json_canonicalizer`, both shipping + RFC-faithful; `coset` is "under
   construction," dCBOR a moving draft).
2. **Stringify `chain_seq`** (`"5"`, not `5`) — LBP's only number; stringifying it
   never exercises JCS's IEEE-754-double number path (the ≥2⁵³ silent-mismatch
   footgun), reducing byte-identity to string handling. Zero expressiveness cost.
3. **No unicode normalization** — JCS passes `body` code points verbatim; both impls
   MUST NOT normalize (correct for arbitrary UTF-8).
4. **`lbp_version` stays authoritative** as the v2→**dCBOR-over-COSE** exit for the
   real edge/Headles future (Numeric Reduction turns the footgun into a guarantee;
   genuinely embedded-native). Don't pay the binary + immature-Rust-COSE cost now.
5. **L0 canonical key form = `did:key` multibase** (retires PEM/raw/hex ad-hoc mix).
6. **Sign every bobbin** (per-bobbin Ed25519), plus the per-peer chain — the
   combination is what fiduciary attribution needs and what no single prior-art has.
7. **Migration from YAML is LOW-risk:** fold `body` into a JSON string field, emit
   one object, run JCS. Also *removes* the latent YAML block-scalar multi-encoding
   determinism trap the current L1 carries.

**Blake-ratified scope calls (2026-07-10):**
8. **L2 = flat hash-chain for v1** (MST → v2 via `lbp_version`).
9. **Varsig now** — self-describing signatures from birth; pairs with did:key for a
   fully algorithm-agile identity+signature layer (post-quantum without a break).
10. **Thin spec** — profile pointers for the borrowed ~60%, full rigor for the novel
    ~15%; also the shape that makes the certifying second implementation cheapest.

---

## The thin spec — outline of `LBP-WIRE-v1.md`

Pointers for the borrowed ~60%; full byte-level rigor for the novel ~15%.

1. **Identity (L0)** — *pointer.* A peer is a `did:key` (Ed25519). Name = label.
2. **Bobbin & signing (L1)** — *full rigor.* Signable form = the field object
   canonicalized per `eddsa-jcs-2022` (JCS → SHA-256 → Ed25519), minus the VC
   JSON-LD envelope. `chain_seq` is a string. Signature = **Varsig-wrapped**.
   `content_sha256` = SHA-256(JCS bytes). + the exact field schema.
3. **Chain (L2)** — *full rigor.* Flat per-peer ledger; entry object;
   `entry_hash = SHA-256(jcs_bytes ‖ varsig)`; genesis-adopts; signed-in linkage.
4. **Transparency (L3)** — *pointer + one rule.* Abstract append-only medium; signed
   tuple binds `created_at`; v1 profile = Matrix, anti-truncation profile = RFC-6962
   `tlog-tiles`.
5. **Tension (L4)** — *full rigor, the core.* The only cross-peer verb; reference +
   stance; content-hash binds exact bytes; no-mutation property; threading.
6. **Passport (L5)** — *pointer + succession rule.* Self-issued manifest as a chained
   bobbin; name→key→model; did:webvh-style succession; sovereign issuer=self.
7. **Stake/Mandate (L6)** — *pointer, reserved.* Profile UCAN delegation when built.
8. **Fiduciary identity & contracted-emission** — *full rigor, the other novelty.* A
   peer may declare itself fiduciary-for-X; contracted-emission = an L4 consent
   governing cross-party-boundary flow (the wire form of
   `project_contracted_emission_invariant`).
9. **Conformance (§10-aligned)** — the W4 vectors as the mechanical gate.

## W3 — fork-ledger (RESOLVED 2026-07-10)

Each fork resolved against Blake's three scope calls (flat · Varsig-now · thin) + W1/W2:

1. **L2 structure — flat hash-chain (v1).** [Blake] MST reserved for v2 via
   `lbp_version`; live chains are at seq ≤ 5, so MST's scale wins buy nothing now and
   cost implementability.
2. **Signature envelope — Varsig (self-describing), now.** [Blake] v1 carries Ed25519
   but the alg is in-band, so secp256k1 / P-256 / post-quantum are non-breaking
   additions. Pairs with did:key (self-describing *key*) → the whole
   identity+signature layer is algorithm-agile by construction. The seam can't be
   retrofitted, so it is added at birth.
3. **Spec shape — thin profile + rigorous novel core.** [Blake] Pointers for the ~60%
   borrowed; full byte-level rigor for the ~15% novel. Also makes the certifying
   second implementation cheap (wire existing crates + hand-write the core). Outline
   above.
4. **peer-id = the `did:key` string** (encodes the raw-32 Ed25519 key in multibase).
   Retires W1's three-encodings mess (PEM/b64url/hex). Human `peer_name` demotes to a
   non-authoritative label; identity IS the did:key. Fiduciary peers carry a label
   like "fiduciary-for-X"; the key is still the identity.
5. **L4 reference = keep both** locator `(peer, kind, slug)` + `content_sha256`.
   Locator finds the current version; the hash binds the exact bytes answered.
6. **Retraction = an L4 stance, not a new primitive.** A retraction is a Tension with
   stance `withdraw`/`retract` targeting a prior bobbin by content-hash — already
   expressible; no wire addition. (Reconcile with the existing `retraction.py` at
   spec-write — it may add convenience, not wire.)
7. **`kind`/`slug`/`stance` — keep the permissive safe-char bound**
   (`^[a-z][a-z0-9_-]{0,31}$` etc.), documented as a *safety* bound, NOT a vocabulary
   whitelist: you may coin any value, but it must be pipe-/newline-/filename-safe
   because it rides the L3 pipe-joined transparency line and the on-disk path.
   Preserves the anti-whitelist canon while keeping interop safe.
8. **Transparency line binds the bobbin's `created_at`** (not an independent
   post-time). Makes the signed tuple reconstructable from the bobbin alone and
   removes W1's third timestamp. Small divergence from the current impl (post-time);
   transparency entries are additive/re-postable, so the cost is low.
9. **L3 = abstract append-only medium** with a minimal interface (`append` +
   `read_all`, plus `inclusion_proof` in the anti-truncation profile). v1 profile =
   Matrix room; anti-truncation profile = RFC-6962 `tlog-tiles`. The wire invariant
   is the signed line; the medium is a profile — Matrix-now / Headles-later is a
   profile swap.

## W4 — conformance vectors (DESIGNED; bytes generated at spec-write)

A self-contained vector set so any implementation self-checks without para-bots.
Built from a **fixed, published test keypair** (a known Ed25519 seed → deterministic
did:key), so every byte is reproducible. Coverage matrix:

| Vector | Pins | Shape |
|---|---|---|
| `key` | L0 | seed → raw-32 → `did:key:z6Mk…` (canonical identity encoding) |
| `bobbin-basic` | L1 | fields → exact JCS bytes (hex) → `content_sha256` → varsig(Ed25519) |
| `bobbin-nested` | L1 | a passport-shaped nested object → JCS bytes (the case YAML broke) |
| `chain-3` | L2 | genesis (bootstrap+adopts) + 2 entries → each `entry_hash`, verifies clean |
| `tension` | L4 | a cross-peer tension → the `content_sha256` binding + stance |
| `log-line` | L3 | the signed transparency tuple bytes (binding `created_at`) |
| `chain_seq-string` | L1 | demonstrates `"5"` (string) — never touches JCS's number path |
| `varsig` | agility | the self-describing signature envelope, decoded |

**Honest bound:** W4 designs the vector *schema + coverage*; the concrete hex bytes
are generated once the JCS signing path exists (spec-write / P2), because the bytes
ARE the reference impl's output. The vectors are the mechanical predicate the P3
conformance gate checks.

## Blake-gates — RESOLVED

The three scope forks are decided (2026-07-10): **flat v1 · Varsig now · thin spec.**
Residual small calls, folded into W3 with a recommendation (no longer blocking):
the transparency line binds `created_at` (W3.8); retraction is modeled as an L4
stance (W3.6, confirm vs `retraction.py` at spec-write). Nothing else is
Blake-blocked; the owed step is the ratified spec-write + vector generation, gated
only on distinct-lineage review.

---

## Sources (W2, agent-web-sourced — verify at freeze)

did:key v0.9 (W3C CCG) · DID Core 1.0 (Rec 2022-07-19) · VC Data Model 2.0 +
VC Data Integrity 1.0 + **Data Integrity EdDSA Cryptosuites v1.0 / `eddsa-jcs-2022`**
(Rec 2025-05-15) · RFC-6962 CT / RFC-9162 CTv2 · Sigstore Rekor v2 GA (2025-10-10) +
C2SP `tlog-tiles` · NIP-01 + NIPs issue #354 (serialization under-specified) ·
ActivityPub W3C Rec 2018 + FEP-8b32 (JCS proofs) · AT-proto Repository/Data-Model
(DRISL-CBOR, MST) · UCAN 1.0 (Delegation/Invocation, Varsig) · RFC-8785 JCS +
`rfc8785.py` (Trail of Bits) + `serde_json_canonicalizer` · RFC-8949 §4.2 dCBOR /
RFC-9052 COSE.
