# Bake-off: criterion 1 on Quiet Hours (2026-11-14)

Setup: Pixel_8_API_34 emulator (Android 14), animations off, locale default, clock NOT pinned (Saturday 14 Nov).
Maestro CLI 2.12.1 (analytics off). Author: Claude Code exploring with `maestro hierarchy` and `maestro test`, the CLI equivalents of Maestro MCP's inspect_screen and run tools (Maestro MCP was not loaded in this session).
Clean state per run: Maestro `launchApp clearState: true` with notifications allowed. No emulator snapshot restore yet.

Flow: `criterion1.yaml`. It passed on its first run, written with text locators only, no coordinates.

## Proof attempt 1 (no explicit launch wait)
- good build: 8/10 pass. Runs 6 and 9 failed at setup ("Get Started" not found): blank screen after cold start.
- bug-weekdays-off-by-one (proof): failed at C3 ("Weekdays" not visible). Correct checkpoint.
- bug-next-skips-today (held-out): passed. Not caught.
- Verdict under the spec's rule: rejected_flaky.

## Repair 1: wait up to 20 s for "Get Started" after launch
## Proof attempt 2
- good build: 9/10 pass. Run 10 failed at setup: blank screen for the full 20 s.
- bug-weekdays-off-by-one: failed at C3. Correct checkpoint.
- bug-next-skips-today: passed. Not caught.
- Verdict: rejected_flaky. Second repair deliberately not spent (see below).

## Diagnosis (corrected): harness race, not an app bug
- All 3 hung runs, and a plain-adb repro without Maestro, show the same system log signature: the new app process starts, is killed 68-185 ms later with `Killing <pid>:com.sam.quiethours (adj -10000): remove task`, and 10 s later `failed to attach`. The app never ran, so the blank starting window stayed up.
- Cause: clearing app data queues a task removal. Maestro's `launchApp clearState: true` launches before that removal lands, and the removal kills the fresh process.
- Fix (repair 2): clean state moved out of the flow into `reset.sh`, the Environment manager's job in the spec. It clears data, waits until no task for the app is listed, then grants notifications. The flow only launches.
- Stress check: 0 hangs in 40 cold launches with `reset.sh` (the old order hung on the 2nd launch).

## Proof attempt 3 (reset.sh before each run)
- good build: 10/10 pass (50-56 s per run).
- bug-weekdays-off-by-one (proof): failed at C3. Correct checkpoint.
- bug-next-skips-today (held-out): passed. Not caught, because the clock is not pinned (Saturday: a Weekdays schedule's next start is Monday either way).
- Verdict under the spec's rule: proven ("passed 10/10"; flake rate could still be up to ~26% at 95% confidence).

## What this says about the bake-off question
- A loop-to-green Maestro flow, written by an agent with text locators, passed the proof for criterion 1 once the environment reset was correct. Both rejections came from the harness, not the flow.
- The proof gate still earned its place: it exposed a real reset race that a single green run hides, and it showed the held-out bug escapes without a pinned clock.

## Tooling facts confirmed
- Maestro's Android driver would not start while mobile-mcp's on-device server (`com.mobilenext.mobilecli.DeviceServer`, 30 min idle timeout) was running. Killing it, removing adb forwards and force-stopping `dev.mobile.maestro` fixed it.
- Maestro sees Compose text and content descriptions without test tags.
- Each run's `--test-output-dir` holds commands.json, a screenshot and hierarchy at the failing step, and device logcat, enough to map a failure to a checkpoint in plain code.

## Proof attempt 4 (reset.sh pins the clock to Wed 18 Nov 2026 08:00 IST before each run)
- Clock pinned without root: `settings put global auto_time 0`, `auto_time_zone 0`, `cmd alarm set-timezone Asia/Kolkata`, `cmd alarm set-time <epoch ms>`. Restored with `auto_time 1` after the proof.
- C4 expected text read from the app, not guessed: same-day start shows "Next: Today 9:00 AM".
- good build: 10/10 pass (50-55 s per run).
- bug-weekdays-off-by-one (proof): failed at C3. Correct checkpoint.
- bug-next-skips-today (held-out): failed at C4, showing "Next: Tomorrow 9:00 AM". Now caught.
- Verdict: proven (passed 10/10), and the test catches 1 of 1 held-out bugs.
- Still differs from the agreed criterion 1: the flow uses the wizard's default 9:00 AM-5:00 PM times, not 22:00-07:00 (time-picker steps not written yet).

# Bake-off: criterion 2 (end alarm) on Quiet Hours (2026-11-14)

Criterion: a Silent schedule restores normal sound at its end time. Schedule: the wizard's default Weekdays 9:00 AM-5:00 PM (Ring 0% at start, 70% at end), clock pinned to Wed 18 Nov 2026.
Runner `c2prove.sh` per run: reset.sh, grant DND access (`cmd notification allow_dnd`), clock 08:58, setup flow `c2-setup.yaml`, clock 08:59:55 and wait until the start alarm silences the phone, clock 16:59:15.
- E1 at 16:59:30: probe quiet, and `c2-active.yaml` sees "Active until 5:00 PM".
- E2 by 17:01:00: probe normal, and `c2-ended.yaml` sees "Next: Tomorrow 9:00 AM".
Probe `probe.sh` (read-only): ringer mode from `dumpsys audio`, `zen_mode`, speaker ring volume. Quiet = DND on, ringer not NORMAL, or ring volume 0.

## Results
- good build: 10/10 pass. Sound restored at 17:00:00-17:00:02 every run (DND off, ring 3 -> 4). About 2 minutes per run.
- bug-end-hour-late (proof): failed at E2 sound (still DND at 17:01:00). Correct checkpoint.
- bug-end-5min-early (held-out): failed at E2 sound, not E1 as planned. Caught.
- Verdict: proven (passed 10/10), held-out bug caught.

## Findings
1. Real bug in the good build: Home's status line never refreshes while Home stays open. `ScheduleItem.kt` computes it inside `remember(schedule.id, schedule.days, schedule.startTime, schedule.endTime)`, keyed on nothing time-related. It showed "Next: Today 9:00 AM" through the whole active window and after the end, including across a real minute change. It refreshes only when Home is rebuilt (tab switch or reopen). The status flows switch tabs to work around it; without that, E1's status check fails on the good build.
2. Early-end bug behaviour, verified on device: the END alarm fires at 16:55 but sound stays quiet, because the app re-silences while the schedule window is still open. Nothing ends it at 17:00, so the backup alarm restores sound at about 17:02. The user-visible effect is sound restored 2 minutes late, the same symptom as the hour-late bug.
3. Harness trap: Maestro `launchApp` force-stops the app by default, and force-stop cancels the app's pending alarms. The first trial lost its END and backup alarms that way and stayed silent. Status flows use `launchApp: stopApp: false`.
4. Emulator storage: /data was 96% full (252 MB free) after many installs; a final APK reinstall failed once. The fixture needs a larger or wiped data partition.
5. Clock jumps work for this app: jumping forward over a pending exact alarm made it fire immediately; jumping to just before an alarm let it fire on time.

## Fix for the stale status line (2026-11-14, commit e4ba3eb on claude/dst-safe-schedule-alarms in ~/Desktop/quiet-hours)
- `ScheduleStatus.kt`: new `rememberCurrentMinute()`; it updates at each minute boundary and immediately on ACTION_TIME_CHANGED / ACTION_TIMEZONE_CHANGED.
- `ScheduleItem.kt`: the status `remember` is keyed on that minute and passes it to `scheduleStatus`.
- Unit tests (JDK 21): 219 tests, 0 failures. APK: `../apks/fixed-status.apk`.
- Device check with status flows that never rebuild Home (`c2-active-notab.yaml`, `c2-ended-notab.yaml`):
  - fixed-status: 3/3 pass ("Active until 5:00 PM" during the window, "Next: Tomorrow 9:00 AM" after 17:00, sound restored at 17:00:01-02).
  - original good build: fails at E1 status, as expected.
- Not done: the good-build tag and bug branches still point at the pre-fix code.
