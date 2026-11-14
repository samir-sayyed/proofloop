# 13: Eval runner and baselines

**What to build:** Runs four configurations on the same tasks: one-shot generation, one-shot filtered by the Verifier, an agent running Maestro MCP until green with no proof, and the full loop. Produces a results table of proof rate, held-out bug-catch rate, flake rate, first-run pass rate, cost per accepted test, duration, policy blocks, and human edits.

**Blocked by:** 11, 12

**Status:** done (v0.1)

- [ ] Host and system image recorded with results
- [ ] Development sweeps use three reruns and are labeled provisional
- [ ] Proof-bug catch rate is not reported for configurations that filter on it
- [ ] First baseline recorded
