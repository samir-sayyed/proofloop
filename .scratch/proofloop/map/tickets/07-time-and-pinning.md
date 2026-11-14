# Controlled time and device pinning strategy

**Type:** grilling
**Assignee:** agent
**Blocked by:** 01-maestro-capabilities, 04-emulator-host-setup
**Status:** closed

## Question

How are clock, locale and animation settings pinned per task, and how is time controlled for Quiet Hours schedules so the end alarm is testable deterministically?

## Facts found (not a resolution)

The clock and timezone can be pinned on the emulator without root: `settings put global auto_time 0`, `settings put global auto_time_zone 0`, `cmd alarm set-timezone <Olson id>`, `cmd alarm set-time <epoch ms>`. Setting it before each run from the reset step worked for criterion 1 (see ../../bakeoff/RESULTS.md). Not yet tested: changing the clock mid-flow for criterion 2 and whether the app's exact alarms fire on a clock jump.

Criterion 2 used mid-run clock jumps from the runner (not the flow): jumping over a pending exact alarm fires it immediately, and jumping to just before one lets it fire on time. Never force-stop the app between jumps; it cancels its alarms.

## Resolution

Clock and time zone are pinned without root (cmd alarm set-time / set-timezone, automatic time off) before each run and restored after. Time-dependent checks are runner steps (set_clock, wait_clock, probe) between flows (ADR 0003).
