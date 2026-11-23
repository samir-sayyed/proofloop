# ProofLoop

AI agents can now write Android UI tests in minutes. ProofLoop answers the question that comes next:
**would this test actually turn red if the feature broke?**

An agent writes a deterministic [Maestro](https://maestro.dev) flow from a plain-language acceptance
criterion. ProofLoop accepts it only after proving it:

- it **passes on every clean run** of the good build (10 by default), and
- it **fails at the expected checkpoint** on each seeded-bug build. A crash, a failing tap, or a
  failure at a different checkpoint does not count.

The verdict is plain code. No model decides whether a test is proven. Held-out bugs, never used to
select the test, run afterwards to measure whether the test catches defects it was not tuned for.

- [Results](#results) · [How it works](#how-it-works) · [Install](#install) · [Quick start](#quick-start) ·
  [Commands](#commands) · [Task file](#task-file) · [Writing flows](#writing-flows) · [App maps](#app-maps) ·
  [Verdicts](#verdicts) · [Seeded bugs and builds](#seeded-bugs-and-builds) · [Experiments](#experiments) ·
  [Safety](#safety) · [Limits](#limits) · [Repo layout](#repo-layout)

## Results

**4 of 4 tasks proven on 2 apps, 8 of 8 seeded-bug checks caught at their checkpoints (7 distinct bugs), 0 flakes in 40 good-build runs.**

| Task | Verdict | Good passes | Proof bugs caught | Held-out caught |
|---|---|---|---|---|
| quiet-hours/end-restores-sound | proven | 10/10 | 2/2 | 1/1 |
| quiet-hours/weekdays-listed | proven | 10/10 | 1/1 | 1/1 |
| sunflower/garden-planting | proven | 10/10 | 1/1 | 1/1 |
| quiet-hours/next-start-saved-screen | proven | 10/10 | 1/1 | - |

Apps: Quiet Hours (the author's own sound-scheduling app) and Google's open-source
[Sunflower](https://github.com/android/sunflower). Flows were written by Claude Code with Maestro, text
locators only, no coordinate taps. One proof bug is not hand-written: it is the commit before a real fix.
Pixel 8 emulator, Android 14. "Passed 10/10" still allows a true flake rate up to 26% at 95% confidence;
every report says so.

What the work showed:

- **The proof found a real bug** in the Quiet Hours build everyone called good (Home's status line never
  refreshed while open). It is fixed in the app.
- **Every rejection on the way came from the test harness, not the agent's flows** (a reset race, a
  force-stop that cancelled alarms, an unpinned clock). Log: [docs/what-failed.md](docs/what-failed.md).
- **An app map halves authoring effort but does not change whether a test is proven**, and a map
  that grows between sessions passes learned facts on: [Experiments](#experiments).
- **Fresh agents write tests that look right but hide bugs.** In 6 of 6 trials the author put a wait above the
  checkpoint marker, so the seeded bug failed at setup and was not counted. The flow checker now rejects it.

Details and limits: [docs/results.md](docs/results.md).

## How it works

```
criterion ──► checkpoint plan ──► human approves ──► agent explores the good build ──► Maestro flow
   (skill)      (skill, plan.md)  (proofloop approve:    (Claude Code + Maestro MCP)        (skill)
                                   plan.md hash)                                            │
   report / PR ◄── verdict ◄── 1 good run, each bug build, 9 more good runs ◄── flow check ◄┘
  (runner, only     (runner)            (runner: reset, clock, probes)          (runner: allowlist,
   if proven,                                                                     plan ids)
   hashes match)
```

Three parts:

- **The proofloop skill** ([skills/proofloop/SKILL.md](skills/proofloop/SKILL.md)) guides Claude Code
  through planning checkpoints (a human approves them), exploring with Maestro MCP, writing the flow, and
  at most two evidence-based repairs. The agent never sees the bug builds.
- **The runner** (`proofloop`, Python standard library only) does everything that must be deterministic:
  flow allowlist and checkpoint mapping, app reset, clock and time-zone pinning, read-only sound probes,
  repeated runs, verdict, run record, report, and publishing.
- **The app-map skill** ([skills/app-map/SKILL.md](skills/app-map/SKILL.md)) explores an app once and writes
  `tasks/<app>/app-map.md`: screens, the actions between them, and notes per screen. The test-writing skill
  reads it first and updates it after each proof. Idea from askui's talk on agent test memory
  (nextapp devCon 2026).

Why this split: [docs/adr/0002-skill-plus-runner.md](docs/adr/0002-skill-plus-runner.md). Why prove tests
instead of generating them: [docs/adr/0001-prove-tests-instead-of-generating-them.md](docs/adr/0001-prove-tests-instead-of-generating-them.md).

## Install

You need Python 3.11+, adb (Android SDK platform-tools), the Maestro CLI, and one emulator or device with
USB debugging. Claude Code is needed only to author tests with the skills; the runner works without it.

```bash
git clone https://github.com/samir-sayyed/proofloop && cd proofloop
pip install -e .
```

```bash
brew tap mobile-dev-inc/tap && brew install mobile-dev-inc/tap/maestro
```

For authoring with Claude Code, add Maestro's MCP server and the two skills:

```bash
claude mcp add maestro -- maestro mcp
mkdir -p ~/.claude/skills && cp -R skills/proofloop skills/app-map ~/.claude/skills/
```

Check the setup (adb, a device, Maestro, free space on the device's `/data`):

```bash
proofloop doctor
```

One automation stack per device: do not run mobile-mcp at the same time. Its on-device server holds the only
UI-automation connection and Maestro's driver will not start. `proofloop prepare` and `prove` free it.

## Quick start

### Author a test with Claude Code

In a Claude Code session in this repo, with a task folder for your app (see [Task file](#task-file)):

> Prove a test that a Weekdays schedule shows up on Home.

The skill then:

1. turns the criterion into numbered checkpoints in `plan.md` and asks you to review it; you approve it with
   `proofloop approve TASK --by NAME`;
2. runs `proofloop prepare TASK` (installs the good build, clears data, grants permissions, pins the clock);
3. reads `app-map.md` if there is one, explores the good build with Maestro MCP, and writes `flow.yaml`;
4. runs `proofloop check TASK` until it says `ok`;
5. runs `proofloop prove TASK`, repairs at most twice from the evidence in the record, never weakening an assertion;
6. updates `app-map.md`, shows the report, and offers `proofloop publish` only if the verdict is `proven`.

### Prove a flow you already have

```bash
proofloop check tasks/sunflower/garden-planting/task.json
proofloop prove tasks/sunflower/garden-planting/task.json
```

`check` needs no device. `prove` writes `record.json` and `report.md` under `proofloop-out/` next to the
task (or `--out DIR`) and exits 0 only if the verdict is `proven`.

### Run the whole sample eval

```bash
proofloop eval tasks/ --config "my configuration"
```

prints a results table: proof rate, held-out catch rate, good-build flake rate, coordinate fallbacks,
minutes. Use `--runs 3` for a fast provisional sweep. The task files point at APKs under
`.scratch/proofloop/apks/`, which are not in the repo: build them first
([Seeded bugs and builds](#seeded-bugs-and-builds)).

## Commands

| Command | What it does |
|---|---|
| `proofloop check TASK` | Check the task's flows (allowlist, checkpoints, coordinate fallbacks). No device needed. Also prints whether the approval covers the current plan (a warning only; `prove` enforces it). |
| `proofloop approve TASK --by NAME` | Run by the human who reviewed `plan.md`: writes `approved_by` and `approved_plan` (the plan's sha256) into `task.json`. |
| `proofloop prove TASK [--out D] [--runs N] [--fail-fast]` | Run the proof and write the run record and report. `--runs` overrides `good_runs`; `--fail-fast` stops the good runs at the first failure. |
| `proofloop report RECORD` | Print the markdown report for a run record. |
| `proofloop publish RECORD --repo APP_REPO [--push]` | Commit a **proven** test to the app repo on a `proofloop/<slug>` branch; `--push` also pushes and opens a PR with `gh`. Refuses unproven records, records without artifact hashes, and any flow edited since its proof. Never merges. |
| `proofloop eval DIR [--config NAME] [--runs N] [--out D]` | Prove every task under DIR and print the results table. |
| `proofloop prepare TASK` | Put the device in the task's start state for exploring (good build, clean data, grants, pinned clock). |
| `proofloop restore-clock` | Restore automatic time and time zone. |
| `proofloop probe` | Print the device's sound state (read-only). |
| `proofloop map MAP [FLOWS...]` | Check an app map; with flow files or folders, list screens and actions no flow covers. |
| `proofloop try TASK` | Run the task once on the good build, keep the attempt, and learn from it (use instead of bare `maestro test`). |
| `proofloop learn APP_DIR [--proof D] [--attempts TASK] [--maestro-tests DIR --match S --build B]` | Learn app memory from proofs, kept attempts, or earlier Maestro sessions; writes `app-memory.json` and `learned.md`. |
| `proofloop doctor` | Check adb, a device, Maestro and free space. |

Global option: `--device SERIAL` (default: the only connected device). Exit codes: 0 proven or ok,
1 not proven, 2 usage or setup error (including device errors).

## Task file

A task is a JSON file plus its flows. Paths inside it are relative to the file. Full examples:
[tasks/quiet-hours/](tasks/quiet-hours/) and [tasks/sunflower/](tasks/sunflower/); format in
[proofloop/task.py](proofloop/task.py).

```json
{
  "name": "sunflower/garden-planting",
  "criterion": "Adding a plant lists it on My garden with today's planting date.",
  "app_id": "com.google.samples.apps.sunflower",
  "approved_by": "who approved the checkpoint plan, and when",
  "approved_plan": "sha256:… (written by proofloop approve)",
  "good": "../../../.scratch/proofloop/apks/sunflower-good.apk",
  "bugs": [
    {"name": "garden-wrong-column", "apk": "...", "role": "proof", "expect": "C2"},
    {"name": "date-day-of-year", "apk": "...", "role": "held_out"}
  ],
  "device": {"timezone": "Asia/Kolkata", "clock": "2026-11-18T10:00:00",
             "grants": ["android.permission.POST_NOTIFICATIONS"], "dnd_access": false},
  "good_runs": 10,
  "budget_minutes": 30,
  "steps": [{"flow": "flow.yaml"}],
  "repairs": [{"reason": "...", "change": "..."}]
}
```

| Field | Meaning |
|---|---|
| `approved_by`, `approved_plan` | Who approved the checkpoint plan, and the sha256 of `plan.md` they approved. Both are written by `proofloop approve`. **`prove` returns `needs_human`** if either is missing, if `plan.md` changed since approval, or if the checkpoint ids in the flows and probes differ from the plan's. |
| `good` | The good build. |
| `bugs[].role` | `proof`: must fail at `expect` (a checkpoint id declared in a flow or probe). `held_out`: run after the verdict, never changes it. At least one proof bug is required. |
| `device` | Time zone and pinned clock (needed for time-dependent checks), runtime permissions to grant, and `dnd_access` for apps that change do-not-disturb. |
| `good_runs` | Clean runs of the good build (default 10). |
| `budget_minutes` | Time budget; exceeding it gives `budget_exhausted`. |
| `repairs` | Log of each repair with its reason and change, shown in the report. |

**Steps** run in order, each exactly one of:

| Step | Use |
|---|---|
| `{"flow": "flow.yaml"}` | Run a Maestro flow; failures map to its `# checkpoint:` markers. |
| `{"set_clock": "16:59:15"}` | Set the device clock to HH:MM:SS on the pinned date. |
| `{"wait_clock": "16:59:30"}` | Wait until the device clock reaches HH:MM:SS. |
| `{"probe": {"checkpoint": "E1", "expect": "quiet", "until": "17:01:00"}}` | Read the sound state (`quiet` or `normal`) from `dumpsys audio`, do-not-disturb and ring volume; `until` polls up to a clock time. |

Maestro flows cannot change the clock or read sound state, so time-dependent behaviour uses these runner steps
between flows. See [tasks/quiet-hours/end-restores-sound/](tasks/quiet-hours/end-restores-sound/) for a
probe-based task (an alarm firing at 17:00 restores the phone's sound).

## Writing flows

A flow is a normal Maestro YAML file with comment markers that name its checkpoints:

```yaml
appId: com.sam.quiethours
---
- launchApp:
    stopApp: false
- tapOn: "Add Schedule"
# checkpoint: C1 the wizard opens
- extendedWaitUntil:
    visible: "Step 1 of 2"
    timeout: 10000
- tapOn: "Weekdays"
# checkpoint: C3 the day summary reads "Weekdays"
- assertVisible: "Weekdays"
```

The marker applies to the assertions (`assertVisible`, `assertNotVisible`, `assertTrue`, `extendedWaitUntil`)
that follow it. A command that is not an assertion ends the checkpoint. A failure before the first checkpoint
is `setup`; a failing tap is an `action` failure. Neither counts as catching a bug.

`proofloop check` enforces these rules before any device action:

- **Allowlist:** blocked are `runScript`, `evalScript`, `openLink`, `runFlow`, `retry`, `repeat`,
  `clearKeychain`, `setLocation`, `travel`, `addMedia`, `setAirplaneMode`, `toggleAirplaneMode`, another
  app's `appId`, `clearState: true`, and `stopApp`/`killApp`.
- **`launchApp` needs `stopApp: false`.** The default force-stop cancels the app's pending alarms, and the runner
  already reset the app.
- **Every checkpoint needs an assertion**, and each bug's expected checkpoint must exist in a flow or probe.
- **No wait or assertion right before a checkpoint, outside it.** Put the marker above the wait that gates the
  assertion: a bug that breaks that state would otherwise fail at setup and not count. Waits on a screen anchor
  listed in the app map are allowed.
- **Coordinate taps (`point:`) are flagged** as fallbacks in the report, not blocked.
- Prefer `id:` and text locators, and wait on visible state with `extendedWaitUntil`, never fixed sleeps.
- Multi-line text in one element needs a regex that continues past the first line, for example
  `"Next start: Wed, Nov 18, 9:00 AM.*"`.

## App maps

`tasks/<app>/app-map.md` is memory for the authoring agent: how the app is, not a test.

```markdown
## screen: plant_list
anchors: "Plant list", "Filter by grow zone"
- tap "Avocado" -> plant_detail
- tap "Share" -> ? (not taken: sends to another app)
- rule: 17 plants alphabetically; the filter shows grow zone 9 only
- hazard: the description ends with a link that opens the browser

## route: plant-a-plant
1. garden: tap "Plant list"
2. plant_list: wait for "Avocado", tap "Avocado"
```

Anchors are texts always on that screen. Notes are `precondition`, `rule`, `lookup` or `hazard`. Routes are
navigation only (taps, typing, waits on anchors). Ask Claude Code to "map the app" and the app-map skill explores
breadth-first and writes the file, never taking actions that buy, send, delete or sign out. Then:

```bash
proofloop map tasks/sunflower/app-map.md tasks/sunflower
```

checks the format, flags screens nothing leads to, and lists screens and actions no flow touches (text
matching, not execution). Maps of both sample apps: [Sunflower](tasks/sunflower/app-map.md),
[Quiet Hours](tasks/quiet-hours/app-map.md). Maps hold facts about the good build only, never bug details.

### Self-learning memory

The map is written by people; `learned.md` beside it is written by the runner. Every `proofloop try` and every
`proofloop prove` (good-build runs only) feeds a ledger, `app-memory.json`, from which the runner renders what it
has learned: edges between screens, multi-tap routes, locator fixes (text that failed exactly and passed as a
pattern), slow waits and flaky steps. A fact is a candidate until re-observed, is contradicted when the exact text
later passes, and goes stale when a newer build shows its screen without it. Bug-build runs are never read, and
learned facts never become anchors. `prove` updates `learned.md` and `app-memory.json` beside the app map
(`--no-learn` skips it), and `try` keeps attempts under `<task>/attempts/` with device logs: keep `attempts/` out of
git.

In a live test, three fresh authors given the original map plus memory learned automatically from one earlier
author's attempts all avoided the failure that every author with the original map hit, and all three tests were
proven ([experiments/memory-loop](experiments/memory-loop/README.md)). Design and trade-offs:
[docs/adr/0004](docs/adr/0004-self-learning-app-memory.md).

## Verdicts

| Verdict | Meaning |
|---|---|
| `proven` | every good run passed; every proof bug failed at its expected checkpoint |
| `rejected_flaky` | fewer than `good_runs` passes on the good build |
| `rejected_missed_bug` | a proof bug passed, or failed somewhere else (setup, an action, a crash); the remaining good runs are skipped |
| `blocked_environment` | device or Maestro failure; says nothing about the test |
| `blocked_policy` | the flow uses a command outside the allowlist |
| `needs_human` | no approval bound to the current `plan.md`, checkpoints that differ from the plan, or a flow that cannot be checked |
| `budget_exhausted` | the time budget ran out |

Run order: one good run, then each proof bug, then the remaining good runs, then held-out bugs. A test that
misses a proof bug is rejected after about two runs instead of eleven.

The record (`record.json`) holds every run with its failed step, checkpoint, error, evidence folder
(Maestro commands, screenshot, hierarchy, logcat) and probes, plus `artifacts`: the sha256 of the task file,
`plan.md`, every flow and every APK the proof used. Records are never edited after the fact.
A rule-based labeller (`proofloop/label.py`) classifies failures: environment, bad locator, real bug in the good
build, flaky, missed bug.

## Seeded bugs and builds

A seeded bug is a patch to the app that changes one behaviour. **Proof** bugs select the test; **held-out**
bugs are never shown to the author and measure whether the test catches what it was not tuned for. A seeded
bug must produce the wrong *behaviour*, not just any failure: one first attempt crashed the app at launch
and the gate rightly refused to count it ([docs/what-failed.md](docs/what-failed.md)).

Patches are in `tasks/<app>/bugs/`. The build scripts apply each patch without committing, build a debug APK,
and restore the working tree. Set `JAVA_HOME_21` (Quiet Hours) or `JAVA_HOME_17` (Sunflower) to a working JDK;
JDK 21 is recommended (Java 25 breaks Mockito in unit tests).

**Sunflower is fully reproducible** (Apache-2.0). Building runs the cloned project's Gradle scripts, which is
third-party code: read them first.

```bash
git clone https://github.com/android/sunflower .scratch/oss/sunflower
git -C .scratch/oss/sunflower checkout 2a357a3
tasks/sunflower/build-apks.sh
proofloop prove tasks/sunflower/garden-planting/task.json
```

**Quiet Hours is the author's own app** and its source is not in this repo, so the `quiet-hours` tasks are
worked examples: `tasks/quiet-hours/build-apks.sh APP_REPO BASE_COMMIT` builds the good APK and one per bug
if you have an app that matches. For your own app, copy a task folder, point `good` and `bugs` at your APKs,
write your own patches, and have the skill write the flow.

## Experiments

Both use fresh Claude Code sessions as authors, each in a private folder with only the brief, the good APK, a
logging `maestro` wrapper and a reset script (no bug builds, no existing flows), scored by `proofloop prove`.

- [experiments/map-effect](experiments/map-effect/README.md): 12 trials on Sunflower, with and without the
  app map. The map roughly halved time and tool calls and did not change whether tests were proven. Round 1
  (no flow checker rule): 0 of 6 proven, all hid the bug behind a wait. Round 2 (with the rule): 6 of 6 proven.
- [experiments/memory-loop](experiments/memory-loop/README.md): the same transfer with no hand-written
  update. Memory learned automatically from one author's attempts: 0 of 3 later authors failed on the learned
  quirk (original map: 3 of 3), all proven.
- [experiments/quiet-hours-loop](experiments/quiet-hours-loop/README.md): a first author's write-back added a
  fact to the map (multi-line text needs a regex); 3 later authors with the grown map avoided the failure that
  all 3 with the original map hit (79-111 s vs 134-139 s). The write-back author's flow is now the fourth task.

Samples are small (3 per arm, one criterion, one author model): suggestive, not significant. Each README lists
its limits.

## Safety

- The flow checker blocks scripts, links, nested flows, retries, other apps, force-stops and device state
  changes. It runs in code before any device action.
- Installs, data clearing, permissions, clock and probes happen in the runner, outside the agent's tools.
- Screen text, notifications and logs are data, never instructions (skill rule).
- The agent plans checkpoints and a human approves them with `proofloop approve`, which binds the approval to
  the plan's hash; `prove` refuses if the plan changed or the flows' checkpoints differ from it.
- Unproven tests never open a normal pull request; `publish` refuses them, and refuses a flow whose hash no
  longer matches its proof. ProofLoop never merges.
- Fixtures use synthetic data only. Credentials stay out of records and reports. Run records can contain
  local file paths, and device logs can contain app identifiers such as push tokens: review them before
  sharing and do not commit raw evidence folders (they are git-ignored here).

## Limits

- **Small suite:** 4 tasks on 2 apps and 7 distinct bugs, 6 of them hand-written by the person who built the tool. The
  held-out bugs and the natural pre-fix commit reduce that bias but do not remove it.
- **No baseline comparison yet:** one-shot generation and one-shot-plus-filter are not measured. The flows were
  written by an agent that had already explored the apps, so a fair baseline needs a fresh session.
- **Model cost per test is not measured:** authoring happens in the agent session, which the runner does not meter.
- **One device image and host:** Pixel 8 emulator, Android 14, macOS arm64. Results elsewhere should be labelled separately.
- **Quiet Hours tasks use the default 9:00 AM-5:00 PM schedule**, not overnight windows.
- **App maps:** coverage is text matching, and anchors can exempt a useless wait. Map effects were measured on
  one app each.
- **Device hygiene:** the runner restores the clock and the good build but not do-not-disturb, and a nearly full
  emulator `/data` makes Maestro's driver time out (reported as `blocked_environment`).
- **No license file yet.** Until one is added, all rights are reserved by default.

## Repo layout

```
proofloop/            the runner: task, flow, device, maestro, verify, label, report, evals, appmap, cli
skills/proofloop/     Claude Code skill: plan, explore, write, check, prove, repair, report
skills/app-map/       Claude Code skill: explore an app and write its map
tasks/quiet-hours/    3 tasks, app-map.md, seeded-bug patches, build script
tasks/sunflower/      1 task, app-map.md, seeded-bug patches, build script
experiments/          map-effect and quiet-hours-loop: briefs, setup and scoring scripts, results
docs/                 adr/ (decisions), results.md, what-failed.md, results/ (run records)
tests/                unit tests (fake device, fake Maestro)
.scratch/proofloop/   research brief, decision map, build tickets, bake-off notes
SPEC.md               problem, user stories, decisions
```

## Tests and CI

```bash
python -m unittest discover -s tests
```

The fast tests drive the real verifier with a fake device and fake Maestro and cover every verdict (proven,
flaky, missed bug, wrong checkpoint, failing action, environment failure, install failure, budget, unapproved
plan, blocked commands, coordinate fallback, probe checkpoints, publishing) plus the app-map parser and the
flow-checker rules. GitHub Actions runs them and `proofloop check` on every task, with no device
([.github/workflows/ci.yml](.github/workflows/ci.yml)).

## Project docs

[SPEC.md](SPEC.md) · [docs/adr/](docs/adr/) · [docs/results.md](docs/results.md) ·
[docs/what-failed.md](docs/what-failed.md) · [.scratch/proofloop/](.scratch/proofloop/)
