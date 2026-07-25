---
name: feedback_verify_execution_not_bytes
description: A verification harness's integrity is about EXECUTION, not bytes — freezing the checker's source (hash/chmod/git) doesn't freeze its behavior, because env/interpreter/sys.path/__pycache__/cwd are all agent-reachable inputs. And "measure the artifact by importing it" is safe under a cooperative agent, a vulnerability under an adversarial one — same code, threat set by the agent's CAPABILITY not the loop's INTENT.
metadata:
  type: feedback
interpreted_by: claude-opus-4-8
originSessionId: 2026-06-02__51ddba43 — ralph garage stall (done-check gate; 3-lens design-attack + 2 empirical cross-instance verify rounds)
---

When you build a harness that judges an agent-edited artifact, **content-integrity is not
execution-integrity.** Freezing the checker's *bytes* (a git-hash / `chmod a-w` / a `git status`
preflight) does not freeze what it *does* — because behavior = bytes × interpreter × environment
× filesystem-at-runtime, and every one of those is an input the agent can reach. The ralph
design-attack proved the naive trust boundary (git-tracked source bytes) was the WRONG one: the
real attack surface was the EXECUTION layer — `sys.path` import of the workspace,
`sitecustomize.py`/`.pth` auto-exec, `__pycache__` poisoning, PATH/cwd hijack of subprocess
checks, and the TOCTOU window between hash-check and exec.

**The threat model is set by the agent's CAPABILITY, not the loop's INTENT.** Sharpest instance:
`import target` to measure it is *fine* under a cooperative optimizer and a *vulnerability* under
an adversarial brute-forcer — identical code, different threat model, zero code change. Verified
live (2026-06-02): `garage/autoresearcher/harness.py:93-96` does
`sys.path.insert(0, HERE); import target.compress; cmod.compress(...)` — it executes the
agent-edited target in the judge's own process. Dormant-low-risk then ONLY because the
autoresearcher's agent is a cooperative token-minimizer. The moment a brute-force /
`--dangerously-skip-permissions` agent sits behind that same pattern, it's a silent false-pass
channel. (HARDENED 2026-06-02: the harness now runs the candidate in an isolated child via
`_runner.py` — payload-in/JSON-out, judge re-scores returned data; self-test + independent
cross-instance re-attack both confirm vuln-closed for the in-process measurement-corruption
channel. Residual: the child still has a writable cwd, so it can poison `fixtures/contract.json`
cross-run — same root as the daemon-TOCTOU. A cheap interim re-hash guard (fingerprint the
frozen inputs before the child, re-check after, abort with HARNESS-TAMPER exit 5 on change)
now makes that poisoning LOUD + halting cross-run instead of silent; PREVENTION (deny the
write at all) still needs the sandbox-exec brief.)

**Why:** verification substrate ([[feedback_builder_cannot_self_verify]],
[[project_routine_verify_triad]]) is only as good as its weakest execution input; a checker that
can be steered by what it's checking proves nothing. Coherence-of-the-frozen-source ≠
integrity-of-the-verdict.

**How to apply (the ralph floor):**
1. **Inspect the artifact as DATA, never `import` it** — `ast.parse` text, grep bytes. Run
   product code only as a CHILD SUBPROCESS and assert on its stdout/exit, so the verdict is a
   fact about behavior, not a value the artifact returned into the judge's namespace.
2. **Harden the judge's interpreter**: `python -S -E -I -B` via `env -i` (no site/sitecustomize,
   no PYTHON* env, isolated sys.path, no .pyc); scrubbed absolute-tool PATH; neutral cwd (no
   workspace `conftest.py`/`sitecustomize.py` autoload).
3. **Re-hash the frozen checker in the SAME critical section as exec, before every run** (incl.
   repeats). This — NOT `chmod a-w` (cosmetic vs a same-user process: it can `chmod u+w` and
   rewrite) — is the integrity guarantee. It catches static tamper; it does NOT close the TOCTOU
   race against a persistent daemon (proven winnable ~1/30 in a faithful reimplementation, 0/29
   through real ralph). That needs an OS sandbox (kill stray procs + deny writes outside the
   workspace). See [[project_garage_phase]] ralph stall + brief `ralph_sandbox_exec`.
4. **A test environment distinguishable from production is gameable.** The env-scrubbing that
   hardens (2) is itself a fingerprint a product can sniff (`PYTHONHASHSEED==0`, no `TERM`) to
   behave-only-under-test — Dieselgate shape, a [[project_autonomy_measurement_goodhart]]
   instance. Move unforgeable-ness off environment-secrecy and onto a per-run random CHALLENGE
   the artifact must transform (a nonce it can't precompute), not a fixed expected output.

Sibling to [[feedback_no_fabricated_results]] (the verdict must flow through a channel the
producer can't fake) and [[feedback_verify_across_instances]] — and it adds a cross-MODE axis:
**analytical design-attack and empirical execution-attack are NON-REDUNDANT.** The design-attack
caught the architecture (the wrong trust boundary; the loop-termination ≠ graduation split) that
running would never surface; the empirical attack caught the implementation (chmod-cosmetic,
exit-code-only verdict, race=1/30) that analysis plausibly rubber-stamped. Use both — neither
subsumes the other.