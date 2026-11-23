# Proven: quiet-hours/next-start-saved-screen

**Criterion:** After a Weekdays schedule is activated on a Wednesday morning, the Routine saved screen states the next start as today at 9:00 AM.

**Verdict:** `proven`. passed 10/10; every proof bug failed at its expected checkpoint

**Good build:** passed 10/10 clean runs. With no failures in 10 runs, the true flake rate could still be up to 26% (95% confidence).

| Run | Result | Checkpoint | Step | Seconds |
|---|---|---|---|---|
| 1 | pass |  |  | 65.3 |
| 2 | pass |  |  | 65.7 |
| 3 | pass |  |  | 67.3 |
| 4 | pass |  |  | 72.1 |
| 5 | pass |  |  | 67.6 |
| 6 | pass |  |  | 79.2 |
| 7 | pass |  |  | 79.2 |
| 8 | pass |  |  | 69.9 |
| 9 | pass |  |  | 71.9 |
| 10 | pass |  |  | 65.4 |

**Seeded bugs:**

| Bug | Role | Expected checkpoint | Failed at | Caught | Evidence |
|---|---|---|---|---|---|
| next-skips-today | proof | A2 | A2 | yes | /private/tmp/claude-501/-Users-samirsayyed--claude-spares-spare-wNcq8r/1e660a57-bb79-43b2-bb6d-a441a248d1c9/scratchpad/qh-nextstart3/next-skips-today-1/step1-flow/2026-11-23_125654/flow |

Held-out bugs are run after the verdict and never change it.

**Coordinate fallbacks:** 0

**Repairs made before this proof:**

- re-proved on main b41de64 (2026-11-23): 0/10 good runs; one-time tip bubbles from PR #76 dim Home and the wizard, so 'Manage your sound profiles' and 'Step 1/2 of 2' were not visible: optional taps on "Skip|Got it" before the waits the bubbles block (no runFlow: the app repo's own fix used runFlow when:, which the allowlist blocks); no checkpoint or assertion changed
- re-proof after the first repair: 4/10, the 'Schedule Details' wait sometimes landed behind a wizard tip (timing race): the same optional "Skip|Got it" taps before that wait; no checkpoint or assertion changed

**Proven against** (sha256, first 12 hex):

- `task.json`: `46b0fb97aa41`
- `plan.md`: `077f36fa71e6`
- `flow.yaml`: `ed3254f63ca6`
- `good-b41de64.apk`: `ae2d097aaa55`
- `bug-next-skips-today-b41de64.apk`: `9353b794d542`

**Video of good run 1:** /private/tmp/claude-501/-Users-samirsayyed--claude-spares-spare-wNcq8r/1e660a57-bb79-43b2-bb6d-a441a248d1c9/scratchpad/qh-nextstart3/good-1/run.mp4

**Duration:** 8.4 min. **Failure label:** `none`.
**Device:** sdk_gphone64_arm64, Android 14, host Darwin arm64, plus 1 more for good runs.
**Approved by:** agent (delegated by Samir in chat, 2026-11-23; plan.md unchanged since Samir's own approval), 2026-11-23.
**Authored by:** not recorded; model cost not measured (no author session in task.json).

Humans merge. ProofLoop never merges its own pull requests.
