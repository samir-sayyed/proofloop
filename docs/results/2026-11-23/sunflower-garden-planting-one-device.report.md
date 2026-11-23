# Proven: sunflower/garden-planting

**Criterion:** Adding a plant to the garden lists it on the My garden tab with today's planting date.

**Verdict:** `proven`. passed 10/10; every proof bug failed at its expected checkpoint

**Good build:** passed 10/10 clean runs. With no failures in 10 runs, the true flake rate could still be up to 26% (95% confidence).

| Run | Result | Checkpoint | Step | Seconds |
|---|---|---|---|---|
| 1 | pass |  |  | 31.5 |
| 2 | pass |  |  | 23.6 |
| 3 | pass |  |  | 21.1 |
| 4 | pass |  |  | 21.1 |
| 5 | pass |  |  | 17.7 |
| 6 | pass |  |  | 19.2 |
| 7 | pass |  |  | 20.1 |
| 8 | pass |  |  | 18.3 |
| 9 | pass |  |  | 17.8 |
| 10 | pass |  |  | 17.9 |

**Seeded bugs:**

| Bug | Role | Expected checkpoint | Failed at | Caught | Evidence |
|---|---|---|---|---|---|
| garden-wrong-column | proof | C2 | C2 | yes | /private/tmp/claude-501/-Users-samirsayyed--claude-spares-spare-wNcq8r/1e660a57-bb79-43b2-bb6d-a441a248d1c9/scratchpad/one-dev/garden-wrong-column-1/step1-flow/2026-11-23_112351/flow |
| date-day-of-year | held-out | any | C3 | yes | /private/tmp/claude-501/-Users-samirsayyed--claude-spares-spare-wNcq8r/1e660a57-bb79-43b2-bb6d-a441a248d1c9/scratchpad/one-dev/date-day-of-year-1/step1-flow/2026-11-23_112722/flow |

Held-out bugs are run after the verdict and never change it.

**Coordinate fallbacks:** 0

**Repairs made before this proof:**

- a proof bug failed at setup, not C2: the first wait expected 'Your garden is empty', which a garden bug can change: wait for the 'Plant list' tab, present in every state; no checkpoint changed

**Proven against** (sha256, first 12 hex):

- `task.json`: `2977fe88e208`
- `plan.md`: `035786307f58`
- `flow.yaml`: `aea928274deb`
- `sunflower-good.apk`: `24384bf455ac`
- `sunflower-bug-garden-wrong-column.apk`: `c011c72b665f`
- `sunflower-bug-date-day-of-year.apk`: `891cf6f6a414`

**Video of good run 1:** /private/tmp/claude-501/-Users-samirsayyed--claude-spares-spare-wNcq8r/1e660a57-bb79-43b2-bb6d-a441a248d1c9/scratchpad/one-dev/good-1/run.mp4

**Duration:** 4.7 min. **Failure label:** `none`.
**Device:** sdk_gphone64_arm64, Android 14, host Darwin arm64.
**Approved by:** agent (delegated by Samir in chat, 2026-11-23; plan.md unchanged since Samir's own approval), 2026-11-23.
**Authored by:** not recorded; model cost not measured (no author session in task.json).

Humans merge. ProofLoop never merges its own pull requests.
