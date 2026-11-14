# Quiet Hours seeded bugs

Drafted from `~/Desktop/quiet-hours` at HEAD 72587d5. Each patch passed `git apply --check` there. Apply each one on its own branch from the good-build tag.

| Patch | Criterion | Role | Must fail at | Change |
|---|---|---|---|---|
| bug-weekdays-off-by-one | 1 | proof | C3 day summary | Weekdays preset uses days 2-6 (Tue-Sat) instead of 1-5 |
| bug-next-skips-today | 1 | held-out | C4 "Next:" time | next-start search starts at tomorrow, skipping today's occurrence |
| bug-end-hour-late | 2 | proof | E2 sound restored | END alarm delay +1 hour |
| bug-end-5min-early | 2 | held-out | E1 still silent | END alarm delay -5 minutes |

Notes found while drafting:
- No existing test covers `scheduleStatus`, `nextScheduleStart`, or the Weekdays preset, so the app's own suite will not catch the criterion-1 bugs.
- `VolumeSchedulerTest` asserts `calculateEndDelay` values, so the app's unit tests will likely catch both criterion-2 bugs. Build bug APKs with `assembleDebug` (not `build`), and note in the writeup that unit tests already guard these.
- bug-end-hour-late: the app's backup alarm still restores sound about 2 minutes after the expected end, so on device the bug shows as a ~2-minute late restore. E2's 60 s window catches it.
- bug-end-5min-early: unverified whether the coordinator re-silences the phone because the schedule window is still open. Confirm on the emulator that E1 actually fails; if not, pick a different held-out bug.
