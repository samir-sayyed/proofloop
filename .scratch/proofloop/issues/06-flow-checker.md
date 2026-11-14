# 06: Flow checker and checkpoint map

**What to build:** Plain code that takes any Maestro flow and the checkpoint plan, maps flow steps to checkpoints, confirms every checkpoint has an assertion and explicit waits, and flags coordinate fallbacks. A flow that fails these checks is not sent to proof.

**Blocked by:** 01

**Status:** done (v0.1)

- [ ] Works on a hand-written flow
- [ ] Every coordinate fallback is flagged
- [ ] A flow with a checkpoint that has no assertion is rejected
- [ ] Coordinate-fallback scenario passes via recorded flows
