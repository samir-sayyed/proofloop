# Research 01: Maestro capabilities against a compiled APK

Ticket: `tickets/01-maestro-capabilities.md`. Sources are the official Maestro docs (docs.maestro.dev) and the official GitHub repo (mobile-dev-inc/Maestro). Fetched 2026-11-10. Docs pages were read through a summarizing fetcher, not raw, so quoted behavior is as reported by that tool. Items marked UNVERIFIED need a hands-on check in phase one. Maestro was not installed locally, so nothing here was run.

## Answers

### 1. Locators
Source: [Core selectors](https://docs.maestro.dev/reference/selectors/core-selectors.md), [Selectors index](https://docs.maestro.dev/reference/selectors)

- **text**: regex ("All text selectors are treated as regular expressions"). On Android it matches the element's `contentDescription` (per the page); a bare string shorthand like `tapOn: "Login"` is a text selector. Whether matching is full-string or partial is not stated outright; the docs imply full-match (`Login` "matches exactly", `.*Continue.*` is "for partial match"). Treat as full-match regex; verify.
- **id**: regex. On Android it "maps to the Resource ID". This is the resource-id locator the SPEC wants. Special regex chars (`$`, `[`) must be escaped.
- **index**: 0-based, picks one of several matches (`index: 2` is the third). The docs do not define match ordering, so index is a weaker locator than id/text.
- **point**: see section 3.
- Also exist: relational selectors (`above`, `below`, `leftOf`, `rightOf`, `containsChild`, `childOf`, `containsDescendants`), state selectors (`enabled`, `checked`, `focused`, `selected`), traits, and width/height matchers.
- Compose apps: test tags only appear as ids if the app sets `testTagsAsResourceId = true`. With no app source this cannot be changed, so Compose elements without exposed resource-ids fall back to text/content-description or point.
- No-source/APK: [Android platform page](https://docs.maestro.dev/get-started/supported-platform/android.md) says Maestro connects over ADB, needs the app already installed (identified by package name `appId`), and claims "zero instrumentation" (no test dependencies, no test APK). The page does not explicitly say "works on an APK without source", but nothing requires source; installation stays in environment setup, matching SPEC.

### 2. Waits and assertions
Sources: [wait guide](https://docs.maestro.dev/advanced/wait), [assertVisible](https://docs.maestro.dev/reference/commands-available/assertvisible), [assertNotVisible](https://docs.maestro.dev/reference/commands-available/assertnotvisible.md), [extendedWaitUntil](https://docs.maestro.dev/reference/commands-available/extendedwaituntil.md)

- `assertVisible` / `assertNotVisible`: poll and retry up to 7 seconds, continue as soon as satisfied, fail after. Accept the same selectors as `tapOn`, including `enabled/checked/focused/selected`. These are the assertion primitives for checkpoints, and they already act as observable-signal waits.
- `extendedWaitUntil`: `visible:` or `notVisible:` selector plus `timeout` in ms; returns early, fails at timeout. Default timeout not documented on the page.
- `waitForAnimationToEnd` with `timeout`; `tapOn` has `retryTapIfNoChange` and `waitToSettleTimeoutMs`.
- `assertTrue` (JS expression) exists but its page content was not retrieved. UNVERIFIED.
- Assertions are UI-hierarchy only. No built-in read of system state (e.g. DND). That confirms the SPEC's need for out-of-flow device-state probes.
- Other relevant commands from the 48-command [list](https://docs.maestro.dev/reference/commands-available.md): `clearState`, `launchApp` (with `clearState`, `permissions`, `arguments`), `setPermissions`, `setLocation`, `setAirplaneMode`, `runFlow`, `runScript`/`evalScript`, `assertScreenshot`, `assertWithAI`. (`assertWithAI` uses an LLM, so it must not be used in generated tests.)
- `launchApp` default: all permissions allowed unless specified ([launchApp](https://docs.maestro.dev/reference/commands-available/launchapp.md)). Granting special permissions like DND access is not shown in these docs; UNVERIFIED.

### 3. Point-tap by coordinate
Source: [tapOn](https://docs.maestro.dev/reference/commands-available/tapon)

Yes. `point: "100,200"` (absolute pixels) or `point: "50%,50%"` (relative to screen). It can be combined with a selector so the point is relative to that element (e.g. `text: ...` with `point: "90%,50%"`). The docs warn coordinates are brittle and device-dependent. Percent form is the better fallback to record (resolution-tolerant); the SPEC's "verified coordinate as flagged fallback" is supported. A generator can mark these with a comment or a distinct pattern so they can be flagged.

### 4. Device clock control
Sources: [travel](https://docs.maestro.dev/reference/commands-available/travel.md), [commands list](https://docs.maestro.dev/reference/commands-available.md), [runScript](https://docs.maestro.dev/reference/commands-available/runscript.md), [PR #2558](https://github.com/mobile-dev-inc/Maestro/pulls?q=shell+command), [devicecloud datetime](https://docs.devicecloud.dev/configuration/device-datetime)

- **Maestro cannot set or mock the device clock.** No command does it. `travel` looks relevant (its first line says "adjusting the device system clock") but its own description, parameters and example (coordinate `points` plus `speed`) show it is GPS-route simulation. Treat it as location only.
- No shell/adb command exists in flows. The PR adding one (#2558) was closed unmerged on 2026-03-06. `runScript`/`evalScript` run JavaScript with `env` and `output`; the docs do not show device or shell access.
- Implication: the clock must be set outside Maestro, by Environment manager (e.g. `adb shell settings put global auto_time 0` then setting the date; the QAWolf docs show that pattern, as reported by search, not a Maestro source) or baked into the snapshot. Third-party cloud services that offer a datetime override are not Maestro itself. Tested time-advance mid-flow (Quiet Hours end alarm) would need the runner to change the clock between Maestro invocations, or split into multiple flows, with `launchApp` `stopApp: false` to keep the app. UNVERIFIED: whether the app picks up a clock jump without restart; this belongs to ticket 07.

### 5. Failure reporting and checkpoint mapping
Source: [Test suites and reports](https://docs.maestro.dev/cli/test-suites-and-reports)

- `maestro test --format junit --output report.xml flow.yaml` (also `html`, `html-detailed`). JUnit `id/name/classname` come from the flow header `name`; `junitId`, `junitClassname`, and extra `properties` keys are configurable.
- Per-flow output dir (`--test-output-dir`): `commands.json` (one entry per executed step with command, `status`, `duration`, `sequenceNumber`, error, artifacts), `screenshots/step-<NNN>-...png` (only the failing step is captured in a normal run), `screen-hierarchy/` JSON for the failing step, `manifest.json`, and `logs/` (flow log, device logs, crash/ANR reports).
- **Mapping to a checkpoint:** the failing step is identifiable by `sequenceNumber` and failed command in `commands.json`. Because ProofLoop generates the flow, it can keep a map from step index to checkpoint id (one assertion per checkpoint, ideally one flow per checkpoint or a recorded index table) and resolve the failing step to a checkpoint in plain code. A crash would surface in `logs/` and as a non-assertion failure, which lets the Verifier distinguish crash vs wrong-checkpoint.
- Not confirmed: whether commands accept a human-readable `label` that appears in `commands.json`/JUnit (the fetched report page did not mention it, and a labels docs URL 404ed). Do not depend on it; use sequence numbers or split flows. UNVERIFIED.

## Risks and gaps for ProofLoop
- Clock control is not available in Maestro; environment must do it. Biggest phase-one spike for Quiet Hours.
- Device-state probes (DND) cannot live in the flow; the runner/Verifier must run them between or after Maestro steps. Since flows cannot call adb, "how probes ship alongside the flow" is: a separate probe step executed by the runner at checkpoint boundaries, which argues for one flow per checkpoint segment or a runner that executes segments in order.
- Open Maestro reliability bugs around adb hangs on Android ([#3658](https://github.com/mobile-dev-inc/Maestro/issues/3658), [#3720](https://github.com/mobile-dev-inc/Maestro/issues/3720), awaiting Maestro 3.0); budget a runner-level timeout and retry on infra failure so it is labeled `blocked_environment`, not a missed bug.
- Compose apps without exposed resource-ids force text or percent-point locators.

## Phase-one checks to run hands-on
1. `id` full-match behavior and `index` ordering on the real Quiet Hours APK.
2. Whether `launchApp` `permissions` can grant notification-policy (DND) access; otherwise grant via adb in environment setup.
3. Failing `assertVisible` produces expected `commands.json` and JUnit entries, and a crash produces a distinguishable artifact.
4. Default `extendedWaitUntil` timeout and whether a `label` appears in reports.
