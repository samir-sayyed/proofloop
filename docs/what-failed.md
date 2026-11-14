# What failed

An honest log of what went wrong while building ProofLoop, in the order it happened, and what each
failure changed. Most of these were found by the proof gate itself.

## 1. The plan was to build something that already existed

The spec planned a custom Compiler from agent traces to Maestro tests. Research before writing code
found Maestro's own MCP server does agent authoring, and agent-device exports Maestro YAML. The Compiler
was deferred and the project refocused on proving tests ([ADR 0001](adr/0001-prove-tests-instead-of-generating-them.md)).
**Lesson:** a day of research saved weeks of building a commodity.

## 2. The first seeded-bug branch swallowed an unrelated change

Creating `proofloop/bug-weekdays-off-by-one` with `git commit -am` also committed an unrelated,
uncommitted documentation edit, and removed it from the working branch. It was recovered from the commit.
**Lesson:** the bug-build script now detaches to a base commit, applies each patch without committing,
builds, and restores the working tree (`tasks/quiet-hours/build-apks.sh`).

## 3. The app's unit tests "failed" 117 times on every build

Android Studio's bundled JDK is Java 25; Mockito cannot mock on it. Every build, good or buggy, showed
the same 117 failures. Corretto 17 could not start Gradle on this macOS. JDK 21 worked: 219 tests, 0
failures on the good build. **Lesson:** a failure that is identical on the good build is not a test result.

## 4. mobile-mcp and Maestro cannot share a device

mobile-mcp starts an on-device server (`com.mobilenext.mobilecli.DeviceServer`, 30-minute idle timeout)
that holds Android's only UI-automation connection. Maestro's driver then fails to start. mobile-mcp's
screenshots and element lists also lagged 1-2 s behind the app, which sent blind taps to the wrong
screen. **Lesson:** one automation stack per device; `proofloop` frees the lock before running.

## 5. The first proof was rejected as flaky, twice

8/10, then 9/10 after adding a wait. Each failure was a blank screen after a cold start. It looked
like an app startup hang. The system log showed otherwise: the new process was killed by a pending
"remove task" from the data clear 68-185 ms after it started. A repro with plain adb hit it on the
second launch. Moving the reset into the runner, with a wait for the old task to go, gave 0 hangs in
40 launches and 10/10 ([ADR 0003](adr/0003-runner-owns-device-state.md)).
**Lesson:** the first wait was a guess and it did not work. Reading the system log found the cause.

## 6. A held-out bug escaped because the clock was not pinned

The "next start skips today" bug passed the test on a Saturday: a weekday schedule's next start is
Monday whether or not today is skipped. With the clock pinned to a Wednesday 08:00, the same test
caught it at C4. **Lesson:** time-dependent checkpoints need a pinned clock, and the expected text must
be read from the app ("Next: Today 9:00 AM"); the first guess ("Wed") was wrong.

## 7. A status check deleted the alarm it was supposed to observe

The first end-alarm run stayed silent after 17:00 on the good build. Maestro's `launchApp` force-stops
the app by default, and Android cancels a force-stopped app's pending alarms. **Lesson:** the flow
checker now rejects any `launchApp` without `stopApp: false`.

## 8. The build everyone called good had a real bug

Home's status line was cached with keys that never included the time, so while Home stayed open it
showed "Next: Today 9:00 AM" through the whole active window. The proof's status check failed on the
good build. It was fixed in Quiet Hours (`rememberCurrentMinute()`, commit e4ba3eb) and verified red/green
on the device: the old build fails the open-Home check, the fixed build passes 3/3.
**Lesson:** this is the point of the tool. A single green run of a flow that reopened the app hid it.

## 9. The early-end bug fooled the plan

The held-out "end fires 5 minutes early" bug was expected to fail at E1 (still quiet 30 s before the
end). It failed at E2 instead. On device, the END alarm did fire at 16:55, but the app re-silenced the
phone because the schedule window was still open, and nothing ended it at 17:00; the backup alarm
restored sound at about 17:02. **Lesson:** held-out bugs measure catching, not the planned checkpoint,
and a bug's user-visible effect can differ from its code change.

## 10. A seeded bug that crashed the app tested nothing

The first Sunflower proof bug changed the My garden query to `NOT IN`. The app then crashed at launch:
the garden view reads `gardenPlantings[0]` for plants that have none. The test "failed", but at setup,
and the gate refused to count it, as the rule says: a crash is not a catch. The bug was replaced with a
realistic one (the subquery selects the planting's `id` instead of `plant_id`), which leaves the garden
empty and fails at C2. **Lesson:** check that a seeded bug produces the wrong behaviour, not just any failure.

## 11. A setup step assumed the starting screen

The same Sunflower run first failed on "Your garden is empty", a setup wait that a garden bug can
change. The wait now targets the "Plant list" tab, which is present in every state. No checkpoint
changed. **Lesson:** setup waits should target what is always on screen; assertions about state belong
in checkpoints.

## 12. Smaller harness bugs

- A zsh default-array value was not word-split, so a 12-run proof ran once.
- The emulator's `/data` reached 96% full after repeated 77 MB installs; one reinstall failed. The
  runner now sizes its free-space check from the APK and reports a clear environment failure.
- The first blind adb taps drifted onto the app's Premium screen. Nothing was purchased (the price was
  still loading), but taps without a fresh screen read are not safe.

## What did not fail

The agent-written Maestro flows. Text locators only, no coordinate taps, and once the harness was
right they passed 10/10 on both criteria and caught every seeded bug.
