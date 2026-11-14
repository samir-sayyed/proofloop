# Results

Measured, not projected. Every number here comes from a run record in [results/](results/).

## Setup

- Apps:
  - Quiet Hours (the author's own app, Compose), base commit e4ba3eb. Seeded bugs:
    [tasks/quiet-hours/bugs/](../tasks/quiet-hours/bugs/), plus the commit before e4ba3eb (72587d5).
  - Sunflower ([android/sunflower](https://github.com/android/sunflower), Apache-2.0, commit 2a357a3).
    Seeded bugs: [tasks/sunflower/bugs/](../tasks/sunflower/bugs/).
- Device: Pixel 8 emulator image (sdk_gphone64_arm64), Android 14, macOS arm64 host. Clock pinned per task.
- Author: Claude Code with Maestro (exploring with the Maestro CLI's hierarchy and test commands, the
  equivalents of Maestro MCP's inspect and run tools). Text and content-description locators only.
- Runner: `proofloop eval tasks` (v0.1), 10 good-build runs per task.

## Final eval (2026-11-14)

**Proof rate 3/3, held-out bug-catch rate 3/3, good-build flake rate 0.0% over 30 runs.**

| Task | Verdict | Good passes | Proof bugs caught | Held-out caught | Coordinate fallbacks | Minutes |
|---|---|---|---|---|---|---|
| quiet-hours/end-restores-sound | proven | 10/10 | 2/2 | 1/1 | 0 | 25.4 |
| quiet-hours/weekdays-listed | proven | 10/10 | 1/1 | 1/1 | 0 | 10.6 |
| sunflower/garden-planting | proven | 10/10 | 1/1 | 1/1 | 0 | 5.8 |

| Bug | Task | Role | Expected | Failed at |
|---|---|---|---|---|
| END alarm one hour late | end-restores-sound | proof | E2 | E2: still do-not-disturb at 17:01 |
| Commit before the status-line fix (72587d5, not hand-written) | end-restores-sound | proof | E1s | E1s: "Active until 5:00 PM" never shown with Home open |
| END alarm 5 minutes early | end-restores-sound | held-out | - | E2: app re-silenced, still do-not-disturb at 17:01 |
| Weekdays preset off by one (Tue-Sat) | weekdays-listed | proof | C3 | C3: "Weekdays" not visible |
| Next start skips today | weekdays-listed | held-out | - | C4: "Next: Today 9:00 AM" not visible |
| Garden subquery selects the wrong column | garden-planting | proof | C2 | C2: garden empty after adding |
| Date format uses day-of-year (`D`) | garden-planting | held-out | - | C3: "Nov 18, 2026" not visible |

"Passed 10/10" bounds a task's true flake rate below 26% at 95% confidence; over all 30 runs the bound
is 9.5%. Neither shows zero.

Seven of seven seeded or natural bugs were caught, each at a checkpoint (never at setup or by a crash).

## How the numbers got here

The Quiet Hours flows went through four proof attempts during the bake-off before the harness was right:

| Attempt | Weekdays-listed good build | Cause of failures |
|---|---|---|
| 1 | 8/10 | reset race: launch killed by pending task removal |
| 2 (wait added) | 9/10 | same race; the wait was a guess |
| 3 (runner reset) | 10/10 | held-out bug missed: clock not pinned |
| 4 (clock pinned) | 10/10 | held-out bug caught |

The end-alarm task found one real bug in the "good" Quiet Hours build (Home's status line never
refreshed while open), fixed in e4ba3eb. Sunflower needed one flow repair (a setup wait that assumed an
empty garden) and one seeded-bug replacement (the first one crashed the app, and the gate refused to
count a crash). Details: [what-failed.md](what-failed.md). Earlier records: [results/earlier/](results/earlier/).

## Limits

- Small suite: 3 tasks on 2 apps, 7 bugs, 5 of them hand-written by the same person who built the tool.
  The held-out bugs and the natural pre-fix commit reduce, but do not remove, that bias.
- No comparison configurations yet (one-shot generation, one-shot filtered by the Verifier). The flows
  were written by an agent that had already explored the apps, so a fair baseline needs a fresh session.
- Model cost per test is not measured; authoring happens in the agent session, which the runner does not meter.
- One device image and one host. Results from other images or hosts should be labelled separately.
- Quiet Hours tasks use the default 9:00 AM-5:00 PM schedule, not overnight windows.
