# The runner owns app reset, clock, and probes; flows only drive the UI

Status: accepted, 2026-11-14

## Context

Three bake-off failures came from flows changing device state:

1. Maestro's `launchApp clearState: true` relaunched the app before Android finished removing the old
   task. The pending removal killed the new process ("remove task" 68-185 ms after start, then "failed
   to attach"): a blank screen in about 1 run in 7. A plain-adb repro without Maestro hit it on the 2nd launch.
2. `launchApp` force-stops the app by default, and a force-stop cancels the app's pending alarms. A
   status check during a schedule's window silently deleted the END alarm under test.
3. Maestro flows cannot set the clock or call adb, so time-dependent checks need something outside the flow.

## Decision

- The runner resets the app before each run: `pm clear`, wait until no task for the app is listed,
  then grant permissions. With this, 40 cold launches had no hangs.
- The flow checker rejects `clearState`, `stopApp`, `killApp`, and any `launchApp` without `stopApp: false`.
- Clock changes, waits, and sound probes are task steps between flows. The clock is pinned without
  root through the alarm service (`cmd alarm set-time`, `set-timezone`, automatic time off) and restored after.

## Consequences

- Flows are simpler and portable; the dangerous device operations are in one audited place.
- A checkpoint can be a probe (E1, E2) rather than a UI assertion, so behaviour the UI does not show is testable.
