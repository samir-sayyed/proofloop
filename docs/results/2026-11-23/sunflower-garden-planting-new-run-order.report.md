# Proven: sunflower/garden-planting

**Criterion:** Adding a plant to the garden lists it on the My garden tab with today's planting date.

**Verdict:** `proven`. passed 3/3; every proof bug failed at its expected checkpoint

**Good build:** passed 3/3 clean runs. With no failures in 3 runs, the true flake rate could still be up to 63% (95% confidence).

| Run | Result | Checkpoint | Step | Seconds |
|---|---|---|---|---|
| 1 | pass |  |  | 19.3 |
| 2 | pass |  |  | 17.3 |
| 3 | pass |  |  | 17.1 |

**Seeded bugs:**

| Bug | Role | Expected checkpoint | Failed at | Caught | Evidence |
|---|---|---|---|---|---|
| garden-wrong-column | proof | C2 | C2 | yes | /private/tmp/claude-501/-Users-samirsayyed--claude-spares-spare-wNcq8r/1e660a57-bb79-43b2-bb6d-a441a248d1c9/scratchpad/sunflower-proof/garden-wrong-column-1/step1-flow/2026-11-23_104340/flow |
| date-day-of-year | held-out | any | C3 | yes | /private/tmp/claude-501/-Users-samirsayyed--claude-spares-spare-wNcq8r/1e660a57-bb79-43b2-bb6d-a441a248d1c9/scratchpad/sunflower-proof/date-day-of-year-1/step1-flow/2026-11-23_104444/flow |

Held-out bugs are run after the verdict and never change it.

**Coordinate fallbacks:** 0

**Repairs made before this proof:**

- a proof bug failed at setup, not C2: the first wait expected 'Your garden is empty', which a garden bug can change: wait for the 'Plant list' tab, present in every state; no checkpoint changed

**Proven against** (sha256, first 12 hex):

- `task.json`: `0dd2b9666079`
- `plan.md`: `035786307f58`
- `flow.yaml`: `aea928274deb`
- `sunflower-good.apk`: `24384bf455ac`
- `sunflower-bug-garden-wrong-column.apk`: `c011c72b665f`
- `sunflower-bug-date-day-of-year.apk`: `891cf6f6a414`

**Duration:** 2.0 min. **Failure label:** `none`.
**Device:** sdk_gphone64_arm64, Android 14, host Darwin arm64.
**Model cost:** not measured by the runner (authoring happens in the agent session).

Humans merge. ProofLoop never merges its own pull requests.
