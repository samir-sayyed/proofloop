# Does a map that grows between sessions help? (Quiet Hours)

Run 2026-11-17 on the Quiet Hours good build (e4ba3eb), Pixel 8 emulator, clock pinned to Wed 18 Nov 2026
08:00 IST, synthetic data only. Same isolation and scoring as [../map-effect](../map-effect/README.md):
private author folder (good APK, logging `maestro` wrapper, `reset.sh`, `check.sh`, `map.md`), no bug builds,
scored by `proofloop prove` (3 clean runs, bug `next-skips-today` must fail at the criterion's second checkpoint).

## Step 1: write-back (growth)

One fresh author wrote criterion A ("after a Weekdays schedule is activated on a Wednesday morning, the
Routine saved screen states the next start as today 9:00 AM") from the checked-in map, and was told to deliver
an updated `map-out.md` of facts it observed.

- Its first run failed: the saved screen's "Next start: ..." line and the end-sound sentence are one
  multi-line text element, so an exact `assertVisible` does not match; a trailing `.*` does.
- It added exactly two `rule:` lines to the `saved` screen recording that. Nothing else changed, nothing was
  invented, no bug information. `proofloop map` accepts the map. Its flow was proven (3/3, bug caught at A2).
- 143 s, 73.9k tokens, 9 tool calls.

## Step 2: does the grown map transfer?

Six fresh authors wrote criterion D (the same check for a **Daily** schedule), three with the original map
and three with the grown map, alternating.

| Trial | Map | Time | Tokens | Tool calls | Maestro calls | First flow run failed | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | original | 139 s | 72.9k | 8 | 4 | yes | proven |
| 2 | grown | 79 s | 71.7k | 5 | 2 | no | proven |
| 3 | original | 134 s | 72.7k | 6 | 4 | yes | proven |
| 4 | grown | 90 s | 72.8k | 6 | 3 | no | proven |
| 5 | original | 139 s | 73.2k | 8 | 4 | yes | proven |
| 6 | grown | 111 s | 71.7k | 5 | 3 | no | proven |

Means: original map 137 s, 72.9k tokens, 7.3 tool calls, 4.0 Maestro calls; grown map 93 s, 72.1k tokens,
5.3 tool calls, 2.7 Maestro calls.

- **All three original-map authors re-discovered the multi-line quirk** (a failed run, then the `.*` fix). **None of
  the three grown-map authors did**: all wrote `.*` first time. That is the learning transferring.
- All six flows were proven, so the grown map saved effort (about a third of the time, one failed run), not correctness.

## Adopted into the repo

- The grown map is now `tasks/quiet-hours/app-map.md`.
- The write-back author's flow is a checked-in task, `tasks/quiet-hours/next-start-saved-screen`, and passed the full gate:
  10/10 clean runs, bug caught at A2 ([record](../../docs/results/quiet-hours-next-start-saved-screen.record.json)).
  Plan approval is the agent's under the owner's standing instruction, as for the other tasks.

## Limits

- One growth author and one map update (two lines); n=3 per arm; one app; one bug. Suggestive, not significant.
- The new fact was easy to learn from one failure, so the original arm lost one run each. A map of facts that are
  harder to discover would show more.
- The criteria are near-duplicates by design (the point was transfer), so the fourth task adds little coverage.
- Two scoring attempts of the growth flow returned `blocked_environment` (Maestro driver timeout with the
  emulator's `/data` 95% full); after freeing space it was clean. The runner did not count them as results.
- After the final proof the emulator was left with do-not-disturb on (`zen_mode` 1); I turned it off by hand.
  The runner restores the clock but not do-not-disturb.
