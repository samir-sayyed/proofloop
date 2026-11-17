# Do app maps help a fresh author session?

Run 2026-11-17. Six fresh Sonnet 5.5 subagents each wrote a Maestro flow for the same new Sunflower
criterion, three with `tasks/sunflower/app-map.md` and three without. ProofLoop scored every flow.

- Criterion: adding two plants (Avocado, Apple) lists both on "My garden". Checkpoints C1, C2 fixed in `brief.md`.
- Isolation: each author got a private folder (brief, good APK, a logging `maestro` wrapper, a reset
  script, and `map.md` for the map arm). No bug builds, flows or task files. Isolation was requested, not enforced.
- Scoring (`score-trial.sh`): flow check, 3 clean runs on the good build, and the seeded
  `garden-wrong-column` bug must fail at C1.
- Order: control, map, control, map, control, map (one emulator, so sequential).

## Results

| Trial | Arm | Time | Tokens | Tool calls | Maestro calls | Good build | Bug caught at C1 |
|---|---|---|---|---|---|---|---|
| 1 | control | 92 s | 70.2k | 6 | 5 | 3/3 | no (setup) |
| 2 | map | 74 s | 68.5k | 4 | 3 | 3/3 | no (setup) |
| 3 | control | 138 s | 72.1k | 8 | 8 | 3/3 | no (setup) |
| 4 | map | 74 s | 68.6k | 4 | 3 | 3/3 | no (setup) |
| 5 | control | 164 s | 75.6k | 9 | 7 | 3/3 | no (setup) |
| 6 | map | 65 s | 68.4k | 3 | 2 | 3/3 | no (setup) |

Means: control 131 s, 72.6k tokens, 7.7 tool calls, 6.7 Maestro calls; map 71 s, 68.5k tokens, 3.7
tool calls, 2.7 Maestro calls. (Trial 1's Maestro count is the total, 5, from a logger fixed afterwards;
trials 1-2 hierarchy/test splits are not comparable.)

## What this shows

- **The map saved effort, not correctness.** Map authors went straight to a passing flow: about half the
  time, half the tool calls, a third of the Maestro calls, about 6% fewer tokens (the map file is read
  into context). Two of three never read the screen. All six flows passed the good build 3/3.
- **No author, with or without a map, produced a proven test.** All six waited for a plant name to be
  visible *above* the checkpoint marker. On the bug build the garden is empty, so that wait fails at
  "setup", which the gate refuses to count. Moving the two markers above their waits in trial 5's flow
  (a manual edit, not an authored trial) gave `proven`: good 3/3, bug failed at C1.
- The map arm's flows copied a "wait for Planted" step from the map's route, so the map carried the habit
  too. The route and the skill now say to assert that state inside a checkpoint (the skill rule is new).

## Limits

- n=3 per arm, one app, one criterion, one author model: the time and call differences are suggestive, not
  significant; the ranges barely separate (control 92-164 s, map 65-74 s).
- The map was written after the garden-planting flow existed, so its route is not independent of the task.
  The criterion differs (two plants, not one with a date), but navigation is shared.
- Fresh author sessions still saw the project's checkpoint rules in the brief, not the full skill.
- A re-run with the fixed skill rule would test whether authors then produce proven tests; not done.
