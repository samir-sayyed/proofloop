# 07: Real verifier

**What to build:** Takes any checked Maestro flow, runs it 10 times from clean snapshots on the good build and against each proof-bug build, uses Maestro's failure output to confirm the failure is at the expected checkpoint, and computes the verdict in plain code. Held-out bugs run only after the verdict and never change it.

**Blocked by:** 02, 06

**Status:** done (v0.1)

- [ ] proven requires 10/10 on the good build and expected-checkpoint failure on every proof bug
- [ ] Works end to end on a hand-written Quiet Hours flow, before any agent exists
- [ ] Crash, install failure, or wrong-checkpoint failure does not count as a catch
- [ ] Environment-failure scenario yields blocked_environment
- [ ] Reports say passed 10/10 and state the 26% flake bound
