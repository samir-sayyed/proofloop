# Self-learning memory: does an automatically learned memory transfer?

Run 2026-11-21. Design: [docs/adr/0004-self-learning-app-memory.md](../../docs/adr/0004-self-learning-app-memory.md).

The earlier [quiet-hours-loop](../quiet-hours-loop/README.md) showed that a fact an author wrote into the map by
hand (the saved screen's "Next start" line and the end-sound sentence are one text element, so the exact text is
not found; a trailing `.*` is) saved later authors a failed run. Here nobody writes anything: `proofloop learn`
extracts facts from good-build runs, and fresh authors get the **original** map plus the generated `learned.md`.

## Offline: what the learner extracts from runs we already had

Inputs: the authoring sessions Maestro kept under `~/.maestro/tests` from the two earlier experiments, and the
Quiet Hours 5.3.3 proof runs. Good-build runs only.

| Input | Facts | Checked against the hand-written map |
|---|---|---|
| Quiet Hours, the growth author's 3 attempts only | 6 edges, 1 locator fix | 6 of 6 edges are in the hand map; the locator fix is the fact that author wrote by hand |
| Quiet Hours, 28 authoring sessions + 3 proofs on 5.3.3 (30 good runs) | 5 edges, 4 routes, 1 locator fix | 5 of 5 edges in the hand map; the locator fix re-observed on 5.3.3 |
| Sunflower, 41 authoring sessions | 1 edge | **wrong**: "Navigate up" -> garden (it goes to the plant list) |

- The first version took the last of several taps as the edge and produced 3 wrong edges (for example welcome
  -> home via "Continue"). Several taps between two recognised screens are now a *route*, not an edge.
- The Sunflower error comes from the human anchors: "My garden" is a tab label shown on both tabs, so seeing it
  does not prove the garden screen is open. Re-observation then "confirmed" the wrong edge 11 times. Recurrence
  shows consistency, not truth: anchor quality limits what the learner can get right.
- No bug-build run was read (unit test: a record with a bug run yields no facts from it; a bug build label is
  refused). The learner writes only `app-memory.json` and `learned.md`, never `app-map.md` or its anchors.

## Live: fresh authors with only the learned memory

Same criterion D as before (a Daily schedule activated on a Wednesday morning; the Routine saved screen states the
next start as today 9:00 AM), same brief plus one line pointing at `learned.md`, good build `e4ba3eb`, Pixel 8
emulator, Android 14 (`emulator-5556`). Memory: learned only from the growth author's 3 attempts
([learned-from-growth-author.md](learned-from-growth-author.md)). Scored by `proofloop prove` (3 clean runs, bug
`next-skips-today` must fail at D2).

| Trial | Time | Tokens | Tool calls | Maestro calls | Failed on the multi-line text | Verdict |
|---|---|---|---|---|---|---|
| 1 | 291 s* | 82.4k | 14 | 11 | no | proven |
| 2 | 77 s | 74.0k | 3 | 2 | no | proven |
| 3 | 82 s | 74.1k | 3 | 2 | no | proven |

\* Trial 1 was slowed by my harness: its `reset.sh` had a quoting bug, so the app was never reset, and the
emulator ran out of storage. All 5 of its failed runs failed at "Get Started" (app not fresh); none touched the
learned fact. Trials 2 and 3 ran with the fixed script.

Compared with the earlier arms on the same criterion (from [quiet-hours-loop](../quiet-hours-loop/README.md)):

| Memory given to the author | Failed first run on the multi-line text | Mean time | Mean tool calls |
|---|---|---|---|
| Original map | 3 of 3 | 137 s | 7.3 |
| Map grown by an author by hand | 0 of 3 | 93 s | 5.3 |
| Original map + memory learned automatically | 0 of 3 | 150 s (3 trials); 80 s (trials 2-3, without the harness bug) | 6.7; 3 |

All nine flows in all three arms were proven; memory changes effort, not correctness.

What this shows: the learner reproduced the same fact the growth author once wrote into the map by hand, so the
write step no longer depends on an agent choosing to write it. It does not show the learner finding something an
author would have missed.

## The `try` loop on the device

The live authors above used memory imported from Maestro's kept sessions. The intended path is `proofloop try`, so
it was checked on the device too: a scratch copy of `next-start-saved-screen` with the exact "Next start" text
failed at A2; with `.*` it passed twice. `learned.md` then listed the locator fix as confirmed (failed then fixed in
1 session, fixed form passed 2 times).

## Import isolation

`--maestro-tests` imports only sessions whose log mentions `--match`, and skips any log that mentions a scoring or
proof folder (`/score/`, `/proofloop-out/`, `/eval-out/`) or a `bug-*.apk`. The source counts above equal the
authors' own runs (3 for the growth author; 9, 7 and 12 for the later groups), so no scoring run was imported.

## Limits

- n=3 per arm, one app, one criterion, one learned fact that matters. Different days and emulator instances
  (`emulator-5554` for the earlier arms, `emulator-5556` here). Trial 1 is confounded by the harness bug.
- The fact was learnable because an earlier author failed and fixed it within `maestro test` runs that Maestro kept.
  New sessions must use `proofloop try` (or be imported) for the loop to see their failures.
- Learned edges are only as right as the human anchors (the Sunflower case).
- The emulator's 6 GB data partition ran full during these runs; scoring needed a reboot (and an uninstall) before
  each proof to recover space. The runner reports this as `blocked_environment`, but it cost time.
