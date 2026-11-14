# 02 - mobile-mcp: is its trace rich enough to compile?

Question (ticket 02): do mobile-mcp's element lists, refs and actions capture enough per step (resource id, text, bounds, UI state before/after) to compile a deterministic Maestro test? Does it expose screen recording and logs? What is missing?

## Short answer

Partly. The per-screen element list is rich enough to pick locators (resource id, text, content-desc, bounds, enabled/checked/focused/selected). The server itself records nothing: there is no trace, no step log, no before/after state. ProofLoop's Device boundary must capture a `list_elements` snapshot before and after every action and own the trace. Recording and logs exist. Several gaps (below) must be filled in ProofLoop's wrapper or avoided by design.

## Sources

Primary: installed package `@mobilenext/mobile-mcp` v1.0.16 source in `/Users/samirsayyed/.npm/_npx/3d55143a3497ce4a/node_modules/@mobilenext/mobile-mcp/lib/` (`server.js`, `format-elements.js`, `mobile-device.js`, `android.js`), the bundled `mobilecli` v1.0.22 binary (`--help` output), and https://github.com/mobile-next/mobilecli (README). I had no device attached (`mobile_list_available_devices` returned none), so nothing below is empirically observed on a live Android emulator. Items marked UNVERIFIED need a spike.

## Findings

### 1. Element list content
- Default backend is `mobilecli` (legacy adb/uiautomator path only with `MOBILEMCP_LEGACY_ROBOT=1`) (`server.js:161,226,283`). `mobile_list_elements_on_screen` calls `mobilecli dump ui` and flattens the tree (`mobile-device.js:191-198`).
- Per element, fields carried: `type`, `text`, `label`, `name`, `value`, `identifier`, `rect {x,y,width,height}`, `ref`, `focused`, `selected`, `checked`, `enabled` (`mobile-device.js:7-20`).
- Text format prints `@ref Type text= label= name= value= id= at=x,y size=WxH` plus only non-default states `focused|selected|checked|disabled` (`format-elements.js`). JSON format has the same fields; note `enabled` is emitted only when false, and `selected`/`checked`/`focused` only when true (`format-elements.js:42-61`). Absent therefore means default, which is fine for a recorder but must be interpreted that way.
- Android resource id: in the legacy path `identifier` is the uiautomator `resource-id`, `label` is `content-desc` (`android.js:316-331`). In the mobilecli path the field is named `identifier`; that it carries the Android resource-id is UNVERIFIED without a device (the mobilecli Go source/binary was not inspected; the README does not list dump fields).
- Filtering: legacy path only keeps nodes with text, content-desc, hint, resource-id or checkable (`android.js:316`), and drops zero-size rects. `--full` (raw `dump ui --format raw --full`) returns the unfiltered platform tree, including offscreen nodes, with no refs (`server.js:581-594`; `mobilecli dump ui --help`). The raw format may carry more attributes (class, package, clickable, scrollable, bounds); UNVERIFIED which.
- Not in the list: package name, clickable/scrollable, parent/child hierarchy (flattened), element index/instance among siblings, content of off-screen list items. The Android `hint` is merged into `label`.

### 2. Refs
- `@eN` refs come from the latest dump. Tool text: "Refs and coordinates stay valid as long as the screen does not change; re-list only after navigation or a layout change" (`server.js:581`). Tapping by ref runs `mobilecli io tap <ref>` (`mobile-device.js:166`); double tap resolves the ref via a fresh dump and errors "Element ... not found ... get fresh refs" if absent (`mobile-device.js:174-180`).
- Refs are positional and session-local; they are not stable identifiers and cannot be written into a test. The compiler must resolve ref -> element attributes from the snapshot taken immediately before that action (so the Device boundary has to save the list_elements result and the ref it was used with).
- How refs are generated and whether the same element keeps the same ref across dumps is not documented (README is silent). Treat as unstable.

### 3. Actions available
Tap (ref or x,y), double tap, long press (+duration), swipe, type text, press button (HOME, BACK etc.), open URL (http/https only unless `MOBILEMCP_ALLOW_UNSAFE_URLS=1`), launch/terminate app, install/uninstall app, clear app data, set orientation, fold, set location, clipboard get/set, list apps, foreground app, screenshot (image / save to file) (`server.js` tool list). `mobile_batch_commands` runs many steps, optionally `listElementsAtEnd` (`server.js:925-966`).
- Action tool outputs are one-line strings, e.g. "Clicked on element @e5" / "Clicked on screen at coordinates: x, y" (`server.js:531-536`). A ref-based tap does not return the resolved element or coordinates. So the action log alone does not say what was tapped; correlate with the preceding dump.
- Compilable to Maestro: tap by id/text -> `tapOn: {id|text}`; tap by point -> `tapOn: {point}`; type -> `inputText`; swipe -> `swipe`; BACK -> `back`; launch -> `launchApp`; clear data -> `clearState`; long press -> `longPressOn`; assert from element snapshot -> `assertVisible`. Maestro behavior itself is for ticket on Maestro, not verified here.
- Swipe is coordinate/direction-based with no target element, and there is no scroll-until-visible primitive; compiler must emit `scrollUntilVisible` itself from observed pre/post snapshots.
- Safety mismatch with SPEC: `mobile_install_app`, `mobile_uninstall_app`, `mobile_open_url`, `mobile_clear_app_data`, `mobile_clipboard`, `mobile_set_location` are exposed by default. The SPEC allowlist excludes install/uninstall/arbitrary URLs. mobile-mcp has no allowlist/config to disable tools that I found in `server.js`; the Device boundary must proxy, not pass through, tools (e.g. wrap it as a stdio MCP client and expose only an allowed subset to the agent).

### 4. Trace and state before/after
- mobile-mcp keeps no history. It has no action log, step ids, timestamps in results, or auto snapshot after actions. The only "telemetry" (PostHog/Scarf, `server.js:114-200`) is anonymous usage analytics, disableable with `MOBILEMCP_DISABLE_TELEMETRY`; not a trace. Disable it for ProofLoop (privacy; SPEC requires synthetic data only).
- Actions do not wait for the UI to settle and return nothing about the resulting screen. State-after is only obtained by calling `mobile_list_elements_on_screen` again (or `listElementsAtEnd` in a batch). The agent must be forced (by the Device boundary) to snapshot after each action, or the boundary should do so itself; otherwise transitions and the waits needed (SPEC story 14/21) are not observable. Settling time between action and dump must be measured by the boundary (timestamps are its job), and the compiler should derive waits from "element X appeared" rather than latencies.
- Transient UI (toasts, snackbars) can be missed because each snapshot is a separate round trip.

### 5. Screen recording
- Supported: `mobile_start_screen_recording` (optional `output` .mp4, `timeLimit` seconds) and `mobile_stop_screen_recording` (returns path, size, ~duration) via `mobilecli screenrecord` (`server.js:836-907`). One recording per device. Output path is validated.
- Gap: duration reported is approximate wall clock (`Date.now()` diff); no frame/timestamp index tying actions to video offsets. ProofLoop should record its own start time and per-action timestamps for before/after clips. Android `screenrecord` has a native limit of 3 minutes per file by default (general adb behavior, not confirmed in mobilecli source); UNVERIFIED how mobilecli handles longer sessions.

### 6. Logs
- `mobile_get_device_logs` streams logcat (Android) or unified log (iOS) as JSON lines, with filters `pid, process, tag, level, subsystem, category, message` (key=value / key!=value), `limit` (default small), `saveTo` .log/.txt/.jsonl; stops after `limit` or 30 s silence; only captures logs emitted after the call starts (`server.js:807-827`, `mobile-device.js:235+`).
- It is a bounded pull, not a continuous background stream. SPEC story 15 (logs available while running) needs the Environment manager to run its own `adb logcat` capture to file for the whole run; the MCP tool is only usable for ad-hoc agent looks. Also `mobile_list_crashes` / `mobile_get_crash` exist.
- Log text is untrusted per SPEC; fine, but note the tool returns it to the agent verbatim.

### 7. Other
- Android emulators supported; Maestro-relevant resource ids come through `identifier`. mobilecli starts an on-device agent (`com.mobilenext.mobilecli.DeviceServer`) holding the only UiAutomation connection, so Maestro or other UiAutomator clients cannot run against the same device simultaneously (README of mobilecli). Exploration and Maestro verification must therefore be separate phases (they are in the SPEC), and the DeviceServer may need to be stopped before Maestro runs; UNVERIFIED how.
- License: mobile-mcp package is Apache-2.0-style per npm (not checked here); `mobilecli` is FSL-1.1-ALv2 (`package.json`, README), source-available with a competing-use restriction that converts to Apache after two years. Check fit for a public OSS portfolio project (ProofLoop is not a competing device-control product, but state the dependency).
- `mobile_clear_app_data` exists, which is useful for clean state per run, but SPEC requires emulator snapshots; the Environment manager should restore snapshots rather than rely on it.

## What is missing (for the Compiler's needs)

1. Per-step trace: no built-in record. Build in the Device boundary: step index, timestamp, tool, args, ref -> resolved element (attributes + rect from the preceding dump), pre-snapshot, post-snapshot, screenshot path.
2. Ref-to-element resolution and tap coordinates for ref taps (compute from snapshot rect centre).
3. Settled-state/wait semantics: no wait/idle tool; the compiler must infer `extendedWaitUntil`-style conditions from snapshot diffs.
4. Element hierarchy, clickable/scrollable, package and sibling index (matters for duplicate ids in lists; Maestro supports `index`). Possibly available in `raw --full`; UNVERIFIED.
5. Continuous logs and time-aligned video.
6. Tool allowlist.
7. System-state probes (e.g. DND status) are outside mobile-mcp; they stay in ProofLoop's probe set.

## Recommended spike (needs an emulator)

On one Android emulator with Quiet Hours: (a) dump `list_elements` in json and raw --full on 3 screens; confirm `identifier` equals the `resource-id`, and which extra raw attributes exist; (b) check ref stability across two consecutive dumps; (c) time a tap-then-dump settle; (d) record a 60 s+ video and check the file; (e) confirm tool-list proxying hides install/uninstall/open_url.

## Confidence

High: the tool list, element field set, ref semantics as documented, recording and log tool behavior (read directly from installed source). Medium/UNVERIFIED: whether the mobilecli backend populates resource ids exactly as the legacy path does, raw dump contents, recording length limits, DeviceServer coexistence with Maestro.
