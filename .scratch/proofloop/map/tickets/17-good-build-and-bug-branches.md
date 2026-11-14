# Tag the good build and write the four bug branches

**Type:** task
**Assignee:** samirsayyed
**Blocked by:** 05-first-criterion
**Status:** closed

## Question

User work in ~/Desktop/quiet-hours: tag proofloop/good-5.3.2 from a clean commit, then create proofloop/bug-weekdays-off-by-one, proofloop/bug-next-skips-today, proofloop/bug-end-hour-late and proofloop/bug-end-5min-early from it, and build a debug APK for each. Record APK paths and commit hashes here. Patches and apply steps: ../bugs/README.md (drafted against HEAD 72587d5).

## Resolution

Done 2026-11-14. Debug APKs in `../apks/`, each with distinct compiled code (checked by dex hash).

| Build | Ref | Commit | APK | Existing unit tests (JDK 21, 219 tests) |
|---|---|---|---|---|
| good | tag proofloop/good-5.3.2 | 72587d5 | good-5.3.2.apk | all pass |
| proof bug, criterion 1 | proofloop/bug-weekdays-off-by-one | a3f6f07 | bug-weekdays-off-by-one.apk | all pass (bug not caught) |
| held-out, criterion 1 | proofloop/bug-next-skips-today | 1e23f2a | bug-next-skips-today.apk | all pass (bug not caught) |
| proof bug, criterion 2 | proofloop/bug-end-hour-late | e2f3d48 | bug-end-hour-late.apk | 6 failures (TimeFormatSchedulingTest, VolumeSchedulerTest) |
| held-out, criterion 2 | proofloop/bug-end-5min-early | 44b0f2c | bug-end-5min-early.apk | 6 failures (same classes) |

Manual smoke on Pixel_8_API_34 emulator (Android 14), criterion 1 with default 9:00-17:00 times:
- good: Home lists "Smoke", "Weekdays", "Next: Mon 9:00 AM". C2-C4 pass.
- bug-weekdays-off-by-one: Home lists "Smoke" but "Tue, Wed, Thu, Fri, Sat". Fails at C3 as intended.

Facts later tickets depend on:
- Unit tests need JDK 21. Android Studio's JBR is Java 25 (Mockito cannot mock: 117 failures on every build). Corretto 17 fails to start Gradle on this macOS.
- Fresh install shows onboarding ("Get Started", "Explore App") and a Premium screen ("Continue") before Home. The fixture must get past these, or the clean snapshot must be taken after them.
- Activate shows an "Allow Notifications?" gate. Pre-grant `POST_NOTIFICATIONS` with `pm grant` in environment setup.
- mobile-mcp screenshots and element lists lag about 1-2 s behind transitions, and sometimes return only system UI for the app's Home screen. Explicit waits on visible text are required.
- `uiautomator dump` returned nothing while mobile-mcp's on-device server was running, consistent with the UiAutomation conflict in the mobile-mcp research. Run Maestro with mobile-mcp stopped.
- Default wizard times are 9:00 AM-5:00 PM; criterion 1's 22:00-07:00 still needs time-picker steps.
