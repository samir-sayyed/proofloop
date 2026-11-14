# Maestro MCP bake-off

**Type:** task
**Assignee:** agent
**Blocked by:** 04-emulator-host-setup
**Status:** closed

## Question

Have Claude Code write the first Quiet Hours test with Maestro MCP, then run it 10 times and against the bug build by hand. How often does a loop-to-green test already pass the proof, and why does it fail when it does not? Record results and time per run.

## Progress

Both criteria done, see ../../bakeoff/RESULTS.md. Agent-written Maestro flows plus a runner that owns reset, clock and a sound probe are proven for both (10/10 each); both proof bugs fail at their expected checkpoints and both held-out bugs are caught. Every rejection along the way came from the harness (reset race, force-stop cancelling alarms), and the proof surfaced one real app bug: Home's status line never refreshes while open. That bug is now fixed (Quiet Hours commit e4ba3eb) and verified red/green on device. Remaining before closing: the 22:00-07:00 times.

## Resolution

Both criteria proven; see ../../bakeoff/RESULTS.md and docs/results.md. Closed with the 9:00 AM-5:00 PM default times rather than 22:00-07:00; the overnight variant is a possible extra eval task, not a blocker.
