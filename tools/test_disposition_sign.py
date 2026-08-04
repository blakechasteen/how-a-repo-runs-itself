#!/usr/bin/env python3
"""Regression test for WSH disposition signing (tools/disposition_sign.py).

Pins the properties that make a signed disposition worth more than the JSON
record it accompanies:

  * SIGNER NAME is `session-<sid8>` — byte-identical to the convention
    tension_attest.py:113 shipped and pin_verify.py:201 verifies against. A
    `wsh-<sid8>` variant in a quarantined `.session_keys` registry was built
    first and reverted: it forked a live convention AND was invisible to the
    existing verifier, so every emission reported a false pubkey divergence.
    This test is the tripwire on that regression.
  * KIND MAPPING is conservative — only `declined`/`accepted` claim the
    canonical refusal/consent kinds (`declined` is the one Gate #2 reads);
    reshape/defer/bounce share a neutral kind rather than inflating the
    refusal-family vocabulary to make the corpus look richer than the acts.
  * SLUG stays inside peer_owned_bobbin.SLUG_RE's 64-char ceiling even for the
    longest brief names on disk.
  * FAIL-SOFT is total: unknown kind, absent interpreter, unparseable emitter
    output all return None and never raise. Signing is additive — an unsigned
    event must still be a recorded event, or recording gets expensive and the
    WSH suggestion-not-directive property dies.
  * NO BACKDATING: sign() has no timestamp parameter at all; `created_at` is
    stamped inside PeerOwnedBobbin.create() and signed with the body.

The crypto round-trip (emit → verify → tamper-detect) needs para-bots' venv +
its peer libs, so it is a separate opt-in leg: it runs only when
PARA_BOTS_ROOT/.venv exists, and it writes exclusively into a temp registry +
temp bobbin root so the real ~/para-bots/.peer_keys is never touched. Skipped
(not failed, not silently passed) when the venv is absent.

Run: ./.venv/bin/python tools/test_disposition_sign.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # tools/ on path
import disposition_sign as ds  # noqa: E402


class TestSignerConvention(unittest.TestCase):
    def test_peer_name_is_the_shipped_session_convention(self):
        self.assertEqual(ds._peer_name("73613a12"), "session-73613a12")

    def test_peer_name_matches_tension_attest_literally(self):
        """The whole point of the revert: one session, one key, one name."""
        sid8 = "abc12345"
        self.assertEqual(ds._peer_name(sid8), f"session-{sid8}")

    def test_peer_name_never_forks_into_a_wsh_namespace(self):
        self.assertFalse(ds._peer_name("73613a12").startswith("wsh-"))

    def test_peer_name_is_sanitised_and_degrades_safely(self):
        self.assertEqual(ds._peer_name("a/b c!"), "session-abc")
        self.assertEqual(ds._peer_name(""), "session-nosid")

    def test_no_separate_keys_namespace_helper_survives(self):
        """A quarantined session-keys dir is the reverted design; if this helper
        comes back, the false-divergence bug comes back with it."""
        self.assertFalse(hasattr(ds, "session_keys_dir"))


class TestKindMapping(unittest.TestCase):
    def test_declined_is_the_canonical_refusal_kind(self):
        # This is the mapping Gate #2's "genuine decline" reads.
        self.assertEqual(ds.KIND_MAP["declined"], "decline_request")

    def test_accepted_is_canonical_consent(self):
        self.assertEqual(ds.KIND_MAP["accepted"], "consent")

    def test_soft_kinds_do_not_inflate_the_refusal_vocabulary(self):
        for k in ("reshaped", "deferred", "bounced"):
            self.assertEqual(ds.KIND_MAP[k], "brief_disposition")

    def test_covers_every_wsh_kind(self):
        import brief_disposition as bd
        self.assertEqual(set(ds.KIND_MAP), set(bd.KINDS))


class TestSlug(unittest.TestCase):
    STAMP = "20260725-205911"

    def test_fits_the_slug_ceiling_for_the_longest_real_brief_name(self):
        longest = "project_c_para_refusal_emitter_design_with_a_very_long_tail.md"
        s = ds._slug(longest, self.STAMP)
        self.assertLessEqual(len(s), 64)

    def test_matches_peer_owned_bobbin_slug_grammar(self):
        import re
        slug_re = re.compile(r"^[a-z0-9][a-z0-9_\-]{0,63}$")  # pob.SLUG_RE
        for name in ("weft_trust_tier_grammar.md", "A-Brief.MD", "x.md",
                     "project_c_para_refusal_emitter_design.md"):
            self.assertRegex(ds._slug(name, self.STAMP), slug_re)

    def test_is_readable_not_just_a_hash(self):
        self.assertIn("weft_trust_tier_grammar",
                      ds._slug("weft_trust_tier_grammar.md", self.STAMP))


class TestFailSoft(unittest.TestCase):
    """Signing is additive; every failure returns None and never raises."""

    def test_unknown_kind(self):
        self.assertIsNone(ds.sign("b.md", "nonsense", "why", "sid8"))

    def test_missing_interpreter(self):
        old = os.environ.get("PARA_BOTS_ROOT")
        os.environ["PARA_BOTS_ROOT"] = "/nonexistent-para-root"
        try:
            self.assertIsNone(ds.sign("b.md", "declined", "why", "sid8"))
        finally:
            os.environ.pop("PARA_BOTS_ROOT", None)
            if old is not None:
                os.environ["PARA_BOTS_ROOT"] = old

    def test_sign_takes_no_timestamp_parameter(self):
        """Anti-backdating is structural, not a policy: there is no way to pass
        a time in. created_at is stamped by create() and signed with the body."""
        import inspect
        params = set(inspect.signature(ds.sign).parameters)
        self.assertFalse(params & {"now", "created_at", "timestamp", "when", "ts"})


def _para_venv() -> Path:
    return ds.para_root() / ".venv" / "bin" / "python"


@unittest.skipUnless(_para_venv().is_file(),
                     f"para-bots venv absent ({_para_venv()}) — crypto leg skipped")
class TestCryptoRoundTrip(unittest.TestCase):
    """emit → verify → tamper-detect, entirely inside a temp registry."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.keys, self.bobbins = t / "keys", t / "bobbins"
        self.keys.mkdir(); self.bobbins.mkdir()
        self._saved = {k: os.environ.get(k)
                       for k in ("PARA_PEER_KEYS_DIR", "PARA_PEER_BOBBINS_DIR")}
        # Quarantine BOTH the registry and the bobbin root: this test must never
        # mint a key into the real ~/para-bots/.peer_keys (which a stray
        # pubkey_matches_current() call will silently do — load_or_create
        # CREATES, despite its docstring claiming it raises on unknown peers).
        os.environ["PARA_PEER_KEYS_DIR"] = str(self.keys)
        os.environ["PARA_PEER_BOBBINS_DIR"] = str(self.bobbins)

    def tearDown(self):
        for k, v in self._saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
        self.tmp.cleanup()

    def test_emit_verifies_and_detects_tampering(self):
        res = ds.sign("regression_brief.md", "declined",
                      "unit-test emission", "73613a12")
        self.assertIsNotNone(res, "emission failed — see stderr")
        self.assertEqual(res["peer"], "session-73613a12")
        self.assertEqual(res["bobbin_kind"], "decline_request")

        probe = (
            "import pathlib, shutil, sys\n"
            "sys.path.insert(0, %r)\n"
            "from bobbins._shared.peer_owned_bobbin import PeerOwnedBobbin\n"
            "b = pathlib.Path(%r)\n"
            "out = {'verify': PeerOwnedBobbin.load(b).verify(),\n"
            "       'pubkey_current': PeerOwnedBobbin.load(b).pubkey_matches_current()}\n"
            "t = b.parent / 'tampered'\n"
            "shutil.rmtree(t, ignore_errors=True); shutil.copytree(b, t)\n"
            "sk = t / 'SKILL.md'\n"
            "sk.write_text(sk.read_text().replace('unit-test', 'TAMPERED'))\n"
            "out['verify_tampered'] = PeerOwnedBobbin.load(t).verify()\n"
            "print(__import__('json').dumps(out))\n"
        ) % (str(ds.para_root()), res["bobbin_dir"])
        p = subprocess.run([str(_para_venv()), "-c", probe],
                           capture_output=True, text=True, timeout=90)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = json.loads(p.stdout.strip().splitlines()[-1])

        self.assertTrue(got["verify"], "signature must verify as written")
        # The regression: a quarantined namespace made this False for every
        # emission, because the verifier resolves names via the default registry.
        self.assertTrue(got["pubkey_current"],
                        "signer must be resolvable in the ordinary peer registry")
        self.assertFalse(got["verify_tampered"],
                         "an edited reason must fail closed")

    def test_chain_opens_lazily_and_orders_emissions(self):
        """seq/prev must make the ORDER provable, not just the acts."""
        a = ds.sign("brief_one.md", "declined", "first", "73613a12")
        b = ds.sign("brief_two.md", "reshaped", "second", "73613a12")
        self.assertIsNotNone(a); self.assertIsNotNone(b)

        # genesis is seq 0, so the first disposition is 1 and they increment
        self.assertEqual(a["chain_seq"], 1)
        self.assertEqual(b["chain_seq"], 2)
        # bootstrap happens once, on the FIRST emission only
        self.assertEqual(a["chain_state"], "bootstrapped")
        self.assertEqual(b["chain_state"], "existing")
        # each links to the previous ledger entry
        self.assertTrue(b["chain_prev"])
        self.assertNotEqual(a["chain_prev"], b["chain_prev"])

        led = json.loads((self.bobbins / "session-73613a12" / "chain.json").read_text())
        self.assertEqual([e["seq"] for e in led["entries"]], [0, 1, 2])
        self.assertIsNone(led["entries"][0]["prev"], "genesis prev must be null")
        self.assertEqual(led["entries"][0]["kind"], "bootstrap")

    def test_chain_verifies_and_seq_is_inside_the_signature(self):
        """If chain_seq weren't signed, ordering would be an assertion about the
        record rather than a property of it — reorderable by anyone with fs access."""
        res = ds.sign("brief_seq.md", "declined", "seq test", "73613a12")
        self.assertIsNotNone(res)
        probe = (
            "import pathlib, sys, json\n"
            "sys.path.insert(0, %r)\n"
            "from bobbins._shared import chain\n"
            "from bobbins._shared.peer_owned_bobbin import PeerOwnedBobbin\n"
            "b = pathlib.Path(%r)\n"
            "rep = chain.verify_chain('session-73613a12')\n"
            "out = {'chain_ok': rep.ok, 'entries': rep.entries_checked,\n"
            "       'problems': rep.problems}\n"
            "sk = b / 'SKILL.md'\n"
            "orig = sk.read_text()\n"
            "sk.write_text(orig.replace('chain_seq: 1', 'chain_seq: 99'))\n"
            "out['verify_after_seq_tamper'] = PeerOwnedBobbin.load(b).verify()\n"
            "sk.write_text(orig)\n"
            "print(json.dumps(out))\n"
        ) % (str(ds.para_root()), res["bobbin_dir"])
        p = subprocess.run([str(_para_venv()), "-c", probe],
                           capture_output=True, text=True, timeout=90)
        self.assertEqual(p.returncode, 0, p.stderr)
        got = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertTrue(got["chain_ok"], got["problems"])
        self.assertEqual(got["entries"], 2)  # genesis + this one
        self.assertFalse(got["verify_after_seq_tamper"],
                         "chain_seq must be covered by the signature")

    def test_chain_reentry_is_idempotent_not_a_second_genesis(self):
        """The realistic failure is bootstrap raising 'already bootstrapped'.
        _ensure_chain must trust the ledger over the exception.

        Also pins slug de-collision: these three emissions land in the same
        second, and two of them name the SAME brief. Before the `-N` retry that
        second one raised 'bobbin already exists' and was lost — while its JSON
        record (which de-collides) survived. One event, two records, one missing.
        """
        ds.sign("brief_a.md", "declined", "opens the ledger", "73613a12")
        slugs = []
        for _ in range(2):
            r = ds.sign("brief_b.md", "deferred", "re-entry", "73613a12")
            self.assertIsNotNone(r, "same-second re-emission must not be dropped")
            self.assertEqual(r["chain_state"], "existing")
            slugs.append(r["slug"])
        self.assertNotEqual(slugs[0], slugs[1], "collided slugs must diverge")
        self.assertTrue(all(len(s) <= 64 for s in slugs), "de-collision must respect SLUG_RE")

        led = json.loads((self.bobbins / "session-73613a12" / "chain.json").read_text())
        genesis = [e for e in led["entries"] if e["kind"] == "bootstrap"]
        self.assertEqual(len(genesis), 1, "exactly one genesis entry")
        self.assertEqual([e["seq"] for e in led["entries"]], [0, 1, 2, 3],
                         "every emission reached the ledger, none lost to collision")

    def test_real_peer_registry_is_untouched(self):
        real = Path.home() / "para-bots" / ".peer_keys" / "registry.json"
        before = json.loads(real.read_text()) if real.is_file() else {}
        ds.sign("regression_brief_2.md", "reshaped", "unit-test", "73613a12")
        after = json.loads(real.read_text()) if real.is_file() else {}
        self.assertEqual(sorted(before), sorted(after),
                         "test emission leaked into the real peer registry")


if __name__ == "__main__":
    unittest.main(verbosity=2)
