# Proven: sunflower/garden-roundone

**Criterion:** Adding a plant to the garden lists it on the My garden tab with today's planting date.

**Verdict:** `proven`. passed 3/3; every proof bug failed at its expected checkpoint

**Good build:** passed 3/3 clean runs. With no failures in 3 runs, the true flake rate could still be up to 63% (95% confidence).

| Run | Result | Checkpoint | Step | Seconds |
|---|---|---|---|---|
| 1 | pass |  |  | 65.9 |
| 2 | pass |  |  | 58.6 |
| 3 | pass |  |  | 51.8 |

**Seeded bugs:**

| Bug | Role | Expected checkpoint | Failed at | Caught | Evidence |
|---|---|---|---|---|---|
| garden-wrong-column | proof | C2 | C2 | yes | /private/tmp/claude-501/-Users-samirsayyed--claude-spares-spare-wNcq8r/1e660a57-bb79-43b2-bb6d-a441a248d1c9/scratchpad/fixdemo-out/garden-wrong-column-1/step1-flow/2026-11-23_111012/flow |
| date-day-of-year | held-out | any | C3 | yes | /private/tmp/claude-501/-Users-samirsayyed--claude-spares-spare-wNcq8r/1e660a57-bb79-43b2-bb6d-a441a248d1c9/scratchpad/fixdemo-out/date-day-of-year-1/step1-flow/2026-11-23_111322/flow |

Held-out bugs are run after the verdict and never change it.

**Coordinate fallbacks:** 0

**Proven against** (sha256, first 12 hex):

- `task.json`: `d546d8b07948`
- `plan.md`: `035786307f58`
- `flow.yaml`: `aea928274deb`
- `sunflower-good.apk`: `24384bf455ac`
- `sunflower-bug-garden-wrong-column.apk`: `c011c72b665f`
- `sunflower-bug-date-day-of-year.apk`: `891cf6f6a414`

**Video of good run 1:** /private/tmp/claude-501/-Users-samirsayyed--claude-spares-spare-wNcq8r/1e660a57-bb79-43b2-bb6d-a441a248d1c9/scratchpad/fixdemo-out/good-1/run.mp4

**Duration:** 5.5 min. **Failure label:** `none`.
**Device:** sdk_gphone64_arm64, Android 14, host Darwin arm64.
**Approved by:** agent (delegated by Samir in chat, 2026-11-23), 2026-11-23.
**Authored by:** not recorded; model cost not measured (no author session in task.json).

Humans merge. ProofLoop never merges its own pull requests.
