# Proven: map-effect/haiku-2

**Criterion:** Adding two different plants to the garden lists both of them on the My garden tab.

**Verdict:** `proven`. passed 3/3; every proof bug failed at its expected checkpoint

**Good build:** passed 3/3 clean runs. With no failures in 3 runs, the true flake rate could still be up to 63% (95% confidence).

| Run | Result | Checkpoint | Step | Seconds |
|---|---|---|---|---|
| 1 | pass |  |  | 57.8 |
| 2 | pass |  |  | 66.5 |
| 3 | pass |  |  | 66.4 |

**Seeded bugs:**

| Bug | Role | Expected checkpoint | Failed at | Caught | Evidence |
|---|---|---|---|---|---|
| garden-wrong-column | proof | C1 | C1 | yes | /private/tmp/claude-501/-Users-samirsayyed--claude-spares-spare-wNcq8r/1e660a57-bb79-43b2-bb6d-a441a248d1c9/scratchpad/trials/haiku-2/score/out/garden-wrong-column-1/step1-flow/2026-11-23_115543/flow |

Held-out bugs are run after the verdict and never change it.

**Coordinate fallbacks:** 0

**Proven against** (sha256, first 12 hex):

- `task.json`: `5fd8f7ce274f`
- `plan.md`: `ff145fa892be`
- `flow.yaml`: `810467377c4f`
- `sunflower-good.apk`: `24384bf455ac`
- `sunflower-bug-garden-wrong-column.apk`: `c011c72b665f`

**Video of good run 1:** /private/tmp/claude-501/-Users-samirsayyed--claude-spares-spare-wNcq8r/1e660a57-bb79-43b2-bb6d-a441a248d1c9/scratchpad/trials/haiku-2/score/out/good-1/run.mp4

**Duration:** 4.3 min. **Failure label:** `none`.
**Device:** sdk_gphone64_arm64, Android 14, host Darwin arm64.
**Approved by:** standing approval, experiments/map-effect brief: the proof bug must fail at C1; plan from author markers, 2026-11-23.
**Authored by:** not recorded; model cost not measured (no author session in task.json).

Humans merge. ProofLoop never merges its own pull requests.
