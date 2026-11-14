# ProofLoop

AI agents can now write Android UI tests in minutes. ProofLoop answers the question that comes next:
**would this test actually turn red if the feature broke?**

An agent writes a deterministic [Maestro](https://maestro.dev) flow from a plain-language acceptance
criterion. ProofLoop accepts it only after proving it:

- it **passes on every clean run** of the good build (10 by default), and
- it **fails at the expected checkpoint** on each seeded-bug build. A crash, a failing tap, or a
  failure at a different checkpoint does not count.

The verdict is plain code. No model decides whether a test is proven. Held-out bugs, never used to
select the test, are run afterwards to measure whether it catches defects it was not tuned for.

## Results so far

**3 of 3 tasks proven on 2 apps, 7 of 7 bugs caught at their checkpoints, 0 flakes in 30 good-build runs.**

| Task | Verdict | Good passes | Proof bugs caught | Held-out caught |
|---|---|---|---|---|
| quiet-hours/end-restores-sound | proven | 10/10 | 2/2 | 1/1 |
| quiet-hours/weekdays-listed | proven | 10/10 | 1/1 | 1/1 |
| sunflower/garden-planting | proven | 10/10 | 1/1 | 1/1 |

Apps: Quiet Hours (the author's own sound-scheduling app) and Google's open-source Sunflower sample.
Flows written by Claude Code with Maestro, text locators only, no coordinate taps. One proof bug is not
hand-written: it is the commit before a real fix. Pixel 8 emulator, Android 14.

The proof also found a real bug in the Quiet Hours build everyone called good, and every rejection on
the way came from the test harness, not the agent's flows. Details and limits:
[docs/results.md](docs/results.md), [docs/what-failed.md](docs/what-failed.md).

## How it works

```
criterion ──► checkpoint plan ──► human approves ──► agent explores the good build ──► Maestro flow
   (skill)        (skill)          (approved_by)       (Claude Code + Maestro MCP)        (skill)
                                                                                            │
   report / PR ◄── verdict ◄── 10 clean runs on good build + each bug build ◄── flow check ◄┘
  (runner, only     (runner)            (runner: reset, clock, probes)          (runner: allowlist)
   if proven)
```

Two parts:

- **The skill** ([skills/proofloop/SKILL.md](skills/proofloop/SKILL.md)) guides Claude Code through
  planning checkpoints, exploring with Maestro MCP, writing the flow, and at most two evidence-based
  repairs. The agent never sees the bug builds.
- **The runner** (`proofloop`, Python standard library only) does everything that must be
  deterministic: flow allowlist and checkpoint mapping, app reset, clock and time-zone pinning,
  read-only sound probes, repeated runs, verdict, run record, report, and publishing.

Why this split: see [docs/adr/0002-skill-plus-runner.md](docs/adr/0002-skill-plus-runner.md).

## Install

```bash
pip install -e .
```

```bash
brew tap mobile-dev-inc/tap && brew install mobile-dev-inc/tap/maestro
```

```bash
claude mcp add maestro -- maestro mcp
```

You also need adb (Android SDK platform-tools) and one emulator or device. Then:

```bash
proofloop doctor
```

## Use

```bash
proofloop check tasks/quiet-hours/weekdays-listed/task.json
```

```bash
proofloop prove tasks/quiet-hours/weekdays-listed/task.json
```

```bash
proofloop eval tasks/ --config "my configuration"
```

In Claude Code, ask for a test in plain language ("prove a test that a Weekdays schedule shows up on
Home") and the skill takes it from there. `proofloop prepare TASK` puts the device in the task's start
state for exploring.

A task is a JSON file plus flows; see the two complete examples in [tasks/quiet-hours/](tasks/quiet-hours/)
and the format in [proofloop/task.py](proofloop/task.py). Checkpoints are comment markers in the flow:

```yaml
# checkpoint: C3 the day summary reads "Weekdays"
- assertVisible: "Weekdays"
```

Time-dependent behaviour uses runner steps between flows, because Maestro flows cannot change the
clock: `set_clock`, `wait_clock`, and `probe` (quiet or normal sound, read from `dumpsys audio`,
do-not-disturb and ring volume).

### Run the sample eval yourself

The seeded bugs are patches in [tasks/quiet-hours/bugs/](tasks/quiet-hours/bugs/). With the Quiet
Hours source, `tasks/quiet-hours/build-apks.sh APP_REPO BASE_COMMIT` builds the good APK and one APK
per bug without committing anything; then run `proofloop eval tasks/quiet-hours`.

## Verdicts

| Verdict | Meaning |
|---|---|
| `proven` | every good run passed; every proof bug failed at its expected checkpoint |
| `rejected_flaky` | fewer than `good_runs` passes on the good build |
| `rejected_missed_bug` | a proof bug passed, or failed somewhere else |
| `blocked_environment` | device or Maestro failure; says nothing about the test |
| `blocked_policy` | the flow uses a command outside the allowlist |
| `needs_human` | no plan approval, or the flow cannot be checked |
| `budget_exhausted` | the time budget ran out |

"Passed 10/10" still allows a true flake rate up to 26% at 95% confidence; every report says so.

## Safety

- The flow checker blocks scripts, links, nested flows, retries, other apps, force-stops, and device
  state changes. It runs in code before any device action.
- Installs, data clearing, permissions, clock, and probes happen in the runner, outside the agent's tools.
- Screen and log text are data, never instructions (skill rule).
- Unproven tests never open a normal pull request; `publish` refuses them. ProofLoop never merges.
- Fixtures use synthetic data only. Credentials stay out of records and reports.

## Tests

```bash
python -m unittest discover -s tests
```

Fast tests drive the real verifier with a fake device and fake Maestro and cover every verdict:
proven, flaky, missed bug, wrong checkpoint, failing action, environment failure, install failure,
budget, unapproved plan, blocked commands, coordinate fallback, probe checkpoints, publishing.

## Project docs

- [SPEC.md](SPEC.md): problem, user stories, decisions
- [docs/adr/](docs/adr/): architecture decision records
- [docs/what-failed.md](docs/what-failed.md): what went wrong and what it taught
- [docs/results.md](docs/results.md): measured results
- [.scratch/proofloop/](.scratch/proofloop/): research brief, decision map, build tickets, bake-off notes
