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
tool calls, 2.7 Maestro calls. (Trial 1's Maestro count is the total, 5, because its logger recorded only the first
argument; fixed before the other trials.)

## What this shows

- **The map saved effort, not correctness.** Map authors went straight to a passing flow: about half the
  time, half the tool calls, a third of the Maestro calls, about 6% fewer tokens (the map file is read
  into context). One of three (trial 6) never read the screen; trial 4's author said it didn't, but its log shows one read. All six flows passed the good build 3/3.
- **No author, with or without a map, produced a proven test.** All six waited for a plant name to be
  visible *above* the checkpoint marker. On the bug build the garden is empty, so that wait fails at
  "setup", which the gate refuses to count. Moving the two markers above their waits in trial 5's flow
  (a manual edit, not an authored trial) gave `proven`: good 3/3, bug failed at C1.
- The map arm's flows copied a "wait for Planted" step from the map's route, so the map carried the habit
  too. The route and the skill now say to assert that state inside a checkpoint (the skill rule is new).

## Re-run with the checker (round 2)

Same criterion, brief and scoring, six new fresh sessions. The brief now says to run `./check.sh flow.yaml`
(the checker above, with the map's anchors in the map arm) and fix every error, as the skill's procedure does.

| Trial | Arm | Time | Tokens | Tool calls | Maestro calls | Good build | Verdict |
|---|---|---|---|---|---|---|---|
| 7 | control | 168 s | 73.5k | 9 | 8 | 3/3 | proven |
| 8 | map | 111 s | 71.7k | 5 | 4 | 3/3 | proven |
| 9 | control | 212 s | 76.2k | 11 | 11 | 3/3 | proven |
| 10 | map | 99 s | 70.9k | 5 | 3 | 3/3 | proven |
| 11 | control | 199 s | 76.0k | 10 | 12 | 3/3 | proven |
| 12 | map | 72 s | 70.6k | 5 | 2 | 3/3 | proven |

Means: control 193 s, 75.2k tokens, 10 tool calls, 10.3 Maestro calls; map 94 s, 71.1k tokens, 5 tool
calls, 3 Maestro calls.

- **All six flows were proven** (round 1: none of six). Each author's first draft failed the checker on
  the marker-before-wait error and was fixed in one step. The bug now fails at C1 in every flow.
- **The map's effect is the same as in round 1:** about half the time and tool calls, a third of the Maestro
  calls, 5% fewer tokens, no change in whether the test is proven.
- Trial 12's flow waits for "Plant list" before C1 on the garden screen. That text is a map anchor, so the
  checker allows it, but it is on both tabs and syncs nothing. The good build passed 3/3, so it did not flake
  here; it shows anchors can exempt a useless wait.
- Scoring detail: `prove` finds the map at `tasks/<app>/app-map.md`. The scorer's task folder had none, so
  trial 12 first came back `needs_human` (checker rejected the anchor wait); with the map beside the task,
  as in the repo layout, it is proven. Trials 8 and 10 were unaffected.

## Changes made from this

- `proofloop check` now rejects a wait or assertion outside a checkpoint that leads straight into one,
  unless it waits on a screen anchor from the app map. It rejects all six authored flows above and accepts
  the fixed one, so this mistake now costs one `check` instead of a full proof run.
- The app-map skill says routes are navigation only (no state waits).

## Round 3: one-shot baseline and a cheaper author model (2026-11-23)

Same criterion, brief (`brief-v2.md`), map and scoring as round 2's map arm, with the checker of 2026-11-23
(checkpoint-cannot-fail rule added). Two new arms, three fresh sessions each:

- **One-shot (Sonnet 5.5):** map and checker, **no device**: no `./maestro`, no reset, no APK
  (`oneshot-addendum.md`). The author writes the flow from the brief and map and stops when `./check.sh` passes.
- **Haiku 5.5, full loop:** the round-2 map arm with a cheaper model: device, map and checker.

| Trial | Arm | Time | Peak context | Checker runs | Maestro test runs | Good build | Verdict |
|---|---|---|---|---|---|---|---|
| 13 | one-shot, Sonnet | 21 s | 76.8k | 2 | 0 | 3/3 | proven |
| 14 | one-shot, Sonnet | 23 s | 78.2k | 2 | 0 | 3/3 | proven |
| 15 | one-shot, Sonnet | 21 s | 76.7k | 2 | 0 | 3/3 | proven |
| 16 | full loop, Haiku | 175 s | 83.2k | 2 | 2 | 3/3 | proven |
| 17 | full loop, Haiku | 180 s | 83.5k | 3 | 2 | 3/3 | proven |
| 18 | full loop, Haiku | 215 s | 89.6k | 4 | 2 | 3/3 | proven |

Peak context is the largest single request, read from each session's transcript by `proofloop/cost.py`; it
matches the per-subagent figure Claude Code reports. Tokens processed across all requests (cache reads
re-counted every turn) were about 370k per one-shot trial and 700-900k per Haiku trial.

- **Running the app was not needed here.** With the app map and the checker, all three one-shot flows were
  proven, in about a fifth of the round-2 map arm's time (94 s). The proof gate is what makes this safe: a
  one-shot flow that was wrong would have been rejected, not merged.
- **Haiku matched Sonnet's proof rate (3/3)** at roughly twice the wall time and a little more context, with
  more checker rounds. The verdict does not depend on the author model, so a cheaper author costs only time.
- **The checkpoint-cannot-fail rule fired** on trials 15 and 17 (a wait on a plant name, then a checkpoint
  asserting the same name). Both authors fixed it in one step.
- One-shot trial 13 waited on the shared "Plant list" tab right before C1. The bug was still caught at C1:
  an anchor wait cannot hide a bug, shared or not. A stricter rule that refused shared anchors was tried and
  reverted (it added checker rounds, not catches).

**Confound: the checker changed between arms.** `check.sh` calls the repo's checker live. The one-shot trials
ran with shared anchors exempting waits. All three Haiku trials ran under a stricter rule that refused waits
on shared anchors, which was reverted afterwards. So the Haiku arm's extra checker rounds are partly the
stricter checker, not only the model. Records and flows: [round3/](round3/).

What this does not show: one criterion on one small app whose map was written after a flow for it existed,
three trials per arm. A one-shot author on an unmapped screen has nothing to go on. The cheaper-model result
is for a short, well-mapped flow.

## Limits

- n=3 per arm per round, one app, one criterion, one author model: the time and call differences are suggestive, not
  significant; the ranges barely separate (control 92-164 s, map 65-74 s).
- The map was written after the garden-planting flow existed, so its route is not independent of the task.
  The criterion differs (two plants, not one with a date), but navigation is shared.
- Fresh author sessions saw the project's checkpoint rules in the brief and a checker script, not the full skill.
- Only one seeded bug and one criterion, so 'proven' here means one proof bug caught at C1.
