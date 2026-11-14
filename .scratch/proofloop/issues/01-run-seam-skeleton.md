# 01: Run seam walking skeleton

**What to build:** A Python package where a Run takes acceptance criteria, builds, approval state and budgets and returns a versioned run record. Scripted model and fake device sit at the edges. Deterministic verdict code decides proven, rejected_flaky, rejected_missed_bug and wrong-checkpoint outcomes; an LLM never decides.

**Blocked by:** None (can start immediately)

**Status:** done (v0.1)

- [ ] Run record is versioned and holds verdict, plan, test, trace ref, flake result, per-bug result, policy blocks, cost, duration
- [ ] Fast tests cover proven, flaky, missed-bug and wrong-checkpoint scenarios through the Run seam
- [ ] A crash or install failure never counts as catching a bug
