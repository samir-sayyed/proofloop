# ProofLoop Spec

Status: implemented (v0.1). Built as a Claude Code skill plus a stdlib Python runner; see README.md and docs/adr/.

## Problem Statement

I am an Android engineer who wants AI agents to help with regression testing, but I cannot trust what they produce.

An agent can explore an app and report success, yet it may take a different path on the next run, so its exploration cannot serve as a CI gate. If I ask an LLM to write a test directly, the test may not run, may depend on brittle locators, or may pass without checking anything meaningful. A green test tells me very little until I know it would turn red when the feature breaks.

Existing mobile agents show that agents can drive devices and collect screenshots or video. That shows what the agent did. It does not show that the resulting test protects the behavior I care about. I also have no measured way to compare approaches, find out why runs fail, or show the cost and reliability of an agent workflow.

As an engineer building a public portfolio, I also need a project whose architecture, evals, trade-offs, and governance can be inspected.

## Solution

ProofLoop takes written acceptance criteria, a good build of an Android app, and one or more seeded-bug builds. A human approves a plan of assertable checkpoints. An agent explores the app on an emulator through Maestro MCP and saves a Maestro flow, which is a deterministic regression test that runs without an LLM. Agent-written tests are now easy to get and hard to trust, so ProofLoop's own work is proving them.

A test is accepted only if it:

- passes repeatedly on the good build from a clean emulator state
- fails on each relevant seeded-bug build at the expected checkpoint

ProofLoop then opens a pull request containing the test, verdict, metrics, and before-and-after recordings for human review. If it cannot prove the test, it says why and does not present the test as trustworthy.

A public eval suite compares ProofLoop with simpler approaches on proof rate, catch rate on held-out bugs the loop never saw, flake rate, cost, and human edits needed. Every run receives a failure label, so repeated failures can drive measured improvements to the agent's skills and prompts.

## User Stories

### Defining the work

1. As an Android engineer, I want to supply acceptance criteria in plain language, so that I do not have to write a test script first.
2. As an Android engineer, I want to point ProofLoop at a good build and seeded-bug builds, so that it can test a real app without modifying its source.
3. As an Android engineer, I want each criterion turned into assertable checkpoints, so that vague requirements become observable outcomes.
4. As an Android engineer, I want to be told when a criterion cannot be observed through the UI or a supported device-state probe, so that I can clarify it instead of receiving a hollow test.
5. As a reviewer, I want to approve or edit the checkpoint plan before exploration, so that the agent does not spend money proving the wrong behavior.
6. As a reviewer, I want to record at approval which checkpoint each proof bug should fail, so that the intended proof is explicit without showing any bug to the Planner or Explorer.
7. As an Android engineer, I want to skip the approval gate only for eval runs using approved fixtures, so that benchmarks can run unattended without weakening normal use.

### Exploring the app

8. As an Android engineer, I want the agent to explore the app on a real emulator, so that the test reflects actual screens and transitions.
9. As an Android engineer, I want each run to start from a clean emulator snapshot, so that one run cannot affect another.
10. As an Android engineer, I want the APK already built before a run starts, so that exploration time is not spent on compilation.
11. As an Android engineer, I want device settings such as locale, animations, and clock to be fixed, so that results are repeatable.
12. As an Android engineer, I want every flow the agent runs and every screen it inspects recorded, so that I can see the observed behavior the test came from.
13. As an Android engineer, I want screenshots and a recording retained with the trace, so that I can inspect what the agent saw.
14. As an Android engineer, I want the agent to wait on observable signals, so that tests and exploration do not rely on arbitrary sleeps.
15. As an Android engineer, I want build, device, and app logs available while work is running, so that the agent can react to failures promptly.
16. As an Android engineer, I want exploration limited by time and cost budgets, so that a confused agent cannot run indefinitely.

### Generating deterministic tests

17. As an Android engineer, I want the agent's exploration saved as a test that needs no LLM to run, so that it can be used as a CI gate.
18. As an Android engineer, I want resource IDs and text preferred as locators, so that tests tolerate layout and resolution changes.
19. As an Android engineer, I want coordinates used only as a recorded fallback, so that a test can still act when no stable locator exists.
20. As a reviewer, I want every coordinate fallback flagged, so that I know which steps are fragile.
21. As an Android engineer, I want explicit wait conditions in the generated test, so that timing does not depend on model latency observed during exploration.
22. As an Android engineer, I want each checkpoint to appear as an assertion, so that the test verifies outcomes instead of merely replaying taps.
23. As a reviewer, I want the generated test to be readable and editable, so that I can own it after merging.

### Proving the test

24. As an Android engineer, I want the test rerun ten times on the good build, so that flaky tests are rejected.
25. As an Android engineer, I want each rerun to start from a clean snapshot, so that the flake rate is meaningful.
26. As an Android engineer, I want the test run against each relevant seeded-bug build, so that I know it detects the failure it claims to detect.
27. As an Android engineer, I want the test to fail at the expected checkpoint, so that an unrelated crash or setup error does not count as catching the bug.
28. As an Android engineer, I want verification performed separately from the agent that explored the app, so that the exploring agent does not grade its own work.
29. As an Android engineer, I want a clear verdict for every run, so that I can tell at once whether the test is trustworthy.
30. As an Android engineer, I want a limited repair loop for fixable failures, so that simple locator or timing problems do not require manual work.
31. As an Android engineer, I want repair to stop at a fixed budget, so that failures end with a diagnosis rather than endless spending.
32. As a reviewer, I want repairs recorded with their reason and result, so that a passing test cannot hide what changed.

### Reviewing results

33. As a reviewer, I want a pull request only after proof succeeds, so that my queue contains evidence-backed changes.
34. As a reviewer, I want recordings of the test failing on the bug build and passing on the good build, so that I can verify the claim quickly.
35. As a reviewer, I want the pull request to include flake rate, bugs caught, cost, duration, and coordinate fallbacks, so that I can judge risk without reading logs.
36. As a reviewer, I want humans to remain responsible for merging, so that the agent cannot approve its own work.
37. As an Android engineer, I want a failed run to produce a useful report, so that I can see where it stopped and why.

### Safety and governance

38. As a security-minded engineer, I want device actions checked against an allowlist in code, so that safety does not depend on model obedience.
39. As a security-minded engineer, I want the agent confined to the target app and approved actions, so that it cannot wander across the device.
40. As a security-minded engineer, I want on-screen and log text treated as untrusted data, so that app content cannot redirect the agent.
41. As a security-minded engineer, I want a test screen containing injected instructions in the eval suite, so that the defense is measured rather than asserted.
42. As a security-minded engineer, I want blocked actions recorded, so that attempted policy violations can be reviewed.
43. As a project owner, I want only synthetic app data used, so that traces and recordings can be published safely.
44. As a project owner, I want credentials kept out of traces, reports, and pull requests, so that published evidence cannot expose secrets.

### Measuring and improving

45. As a project owner, I want a repeatable eval suite of about 15 tasks across Quiet Hours and one open-source app, so that results do not depend on a single demo.
46. As a project owner, I want one-shot generation, one-shot generation filtered by the Verifier, an agent running Maestro MCP until green with no proof, and the full loop compared on the same tasks, so that the value of each stage is measured.
47. As a project owner, I want proof rate, held-out bug-catch rate, flake rate, cost per test, duration, and human edits reported, so that the trade-offs are visible.
48. As a project owner, I want some tasks held out from prompt and skill tuning, so that published numbers are not overfit.
49. As a project owner, I want different model choices compared per role, so that expensive models are used only where evals justify them.
50. As a project owner, I want every run labeled by a small, cheap model, so that failures can be grouped without manual review.
51. As a project owner, I want labels to distinguish environment failures, bad locators, a lost agent, flaky app behavior, policy blocks, and real bugs, so that fixes target the right cause.
52. As a project owner, I want skill and prompt revisions compared on the eval suite, so that improvements are demonstrated.
53. As a maintainer, I want fast tests on every change and real-emulator evals on demand or nightly, so that CI stays useful and affordable.
54. As a maintainer, I want eval regressions to fail the gate, so that quality cannot silently decline.

### Adoption and portfolio evidence

55. As an Android engineer, I want to install ProofLoop as an MCP server or Claude Code skill, so that I can use it in an existing agent workflow.
56. As a hiring manager, I want a concise results table and demo, so that I can assess the work quickly.
57. As a hiring manager, I want architecture decision records and a "what failed" writeup, so that I can evaluate the engineer's judgment.
58. As an outside developer, I want to run a small sample eval from documented steps, so that I can verify the published claims.

## Implementation Decisions

### Modules

- **Planner:** a skill step that converts acceptance criteria into a checkpoint plan and flags criteria that cannot be observed. A human approves it; `approved_by` in the task records that, and `prove` refuses without it.
- **Explorer:** uses an agent with Maestro MCP to drive the emulator, save a Maestro flow, and produce a trace.
- **Device boundary:** the agent's only path to the device. It proxies Maestro MCP, checks each flow against the allowlist before it runs, records what ran, and can be backed by a real emulator or a recorded fake.
- **Flow checker:** plain code that maps flow steps to checkpoints, confirms every checkpoint has an assertion and explicit waits, and flags coordinate fallbacks.
- **Verifier:** runs the test against good and seeded-bug builds and computes the verdict in plain code. It accepts any Maestro flow with a checkpoint map, including one written by hand.
- **Repair:** a skill step: at most two evidence-based fixes, each recorded in the task's `repairs`.
- **Environment manager:** restores clean snapshots, installs builds, and fixes device state.
- **Failure labeler:** assigns one failure label to every completed run, by rules over the run record.
- **Evidence and PR publisher:** collects recordings and metrics and opens the pull request.
- **Eval runner:** runs task sets under each configuration and produces the results table.

### Run contract

- A run takes acceptance criteria, one good build, seeded-bug builds, a plan approval state, and budgets.
- A run produces a run record containing the verdict, checkpoint plan, generated test, trace reference, flake result, per-bug result, repair history, policy blocks, failure label, cost, duration, and evidence references.
- The run record is versioned and is the sole input to the PR publisher, failure labeler, and eval reports.
- Verdicts are `proven`, `rejected_flaky`, `rejected_missed_bug`, `blocked_environment`, `blocked_policy`, `budget_exhausted`, and `needs_human`.

### Proof rules

- `proven` requires ten passes out of ten clean runs on the good build, and a failure at the expected checkpoint on every relevant proof-bug build.
- Ten clean passes do not show a test is free of flakes. They bound its flake rate below about 26% at 95% confidence. Reports say "passed 10/10" and state this bound.
- Seeded bugs are split into proof bugs, which the loop uses to accept or reject a test, and held-out bugs, which are run only after the verdict to measure whether the test catches defects it was not selected on. Held-out results never change a verdict.
- A crash, install failure, or failure at the wrong checkpoint does not count as catching a seeded bug.
- The verdict is calculated by deterministic code. An LLM never decides whether a test is proven.
- A failing or unproven test is never presented as trustworthy and does not open a normal pull request.

### Agent and model design

- The agent is the user's Claude Code session following the ProofLoop skill; planning, exploring, writing flows, and repair are steps of that skill. Flow checker, Verifier, Environment manager, report, publisher, eval runner, and failure labeler are plain code. Add a separate agent only when evals show a measurable benefit (ADR 0002).
- The Planner and Explorer see only the acceptance criteria and the good build. They never receive a seeded-bug build, its diff, or its description.
- Repair runs in a fresh context from the failure evidence. It may see that a proof bug was missed and at which checkpoint, but not the bug's diff.
- The runner is Python with no third-party dependencies. ProofLoop itself makes no model calls.
- Model choice is the agent session's. Per-role model tiers are not built; compare them in evals if they matter.
- The task file and run record are validated, versioned JSON. Failure labels are rule-based until evals show rules mislabel too often.
- ProofLoop's testing procedure ships as a versioned skill, and each revision is evaluated.

### Device layer

- ProofLoop does not build a device-control layer.
- Maestro MCP is the first device backend. It ships inside the Maestro CLI, so the agent explores with the same tool that later runs the test, and ProofLoop has one device stack.
- mobile-mcp and a custom trace Compiler are held back. Build the Compiler only if evals show Maestro MCP authoring loses on proof rate, held-out bug-catch rate, or flake rate.
- ARTEMIS is treated as a possible exploration baseline only. It plans, acts, and checks its own work, and it has no action allowlist or clean snapshot per run.

### Generated tests

- Maestro is the first output format because it can test a compiled APK without app source access. Confirm its locator, wait, and point-tap behavior in phase one, and confirm that its failure output can be mapped to a specific checkpoint.
- Checkpoints on system state that the UI does not show, such as whether do-not-disturb is active, are asserted by read-only device-state probes from a fixed set. Probes run in the test runner and Verifier, outside the agent's tools. Decide in phase one how probes ship alongside the Maestro flow.
- Use one flow per checkpoint segment where the runner must change the clock or run a probe between checkpoints, because Maestro flows cannot set the clock or call adb.
- Compose UI test output is deferred.
- Locators are dynamic first, with verified coordinates as a flagged fallback.
- Generated tests contain explicit wait conditions and no model calls.

### Environment

- Every exploration and verification execution starts from a clean snapshot and discards its state afterward.
- Device image, locale, animation settings, and clock are pinned per task.
- Time-dependent apps, including Quiet Hours, use controlled time.
- Local macOS and Linux with KVM are supported targets. Results from different hosts or system images are not merged without being labeled.

### Budgets and defaults

- Each run has limits for model cost, wall-clock time, and repair attempts.
- The initial repair limit is two attempts. Cost and time limits are set from phase-one measurements.

### Safety

- The device allowlist is enforced in code at the device boundary.
- Allowed actions are limited to observing, interacting with, and launching the target app.
- Maestro MCP's `run` tool accepts arbitrary YAML, so each flow is parsed and checked against an allowed command set before it runs. Cloud tools are not exposed to the agent.
- Installing or removing apps, shell access, arbitrary URLs, and navigation to other apps are excluded from agent tools. Environment setup performs required installs outside the agent's tool access.
- Screen contents, logs, and app text are untrusted data and are clearly separated from instructions.
- Blocked actions are recorded in the run record.
- Published fixtures use synthetic accounts and data only, and credentials are read from the environment and kept out of artifacts.

### Human gates

- Normal runs require approval of the checkpoint plan and human review of the pull request.
- The plan gate can be bypassed only for checked-in, previously approved eval fixtures.
- ProofLoop never merges a pull request.

## Testing Decisions

- A good test checks external behavior through the public run contract. It does not assert prompts, internal calls, private module structure, or the exact path taken by an agent.
- There is one test seam: the Run pipeline. Inputs are acceptance criteria, builds, approvals, and budgets. The observable output is the run record, with any published evidence or pull request produced from it.
- The model and device are substituted at the seam's outer edges. Fast tests use scripted model responses and recorded device replays. Eval runs use real models and emulators.
- Flow checker behavior is tested through the Run seam with recorded flows that represent locator, wait, and fallback cases. A separate seam was considered and rejected to keep the test surface small.
- Fast run-level scenarios must cover:
  - a proven test
  - a flaky test
  - a test that misses a seeded bug
  - failure at the wrong checkpoint
  - an environment failure
  - an unobservable criterion
  - a successful repair
  - an exhausted repair budget
  - a blocked device action
  - injected instructions on screen
  - exhausted cost and time budgets
  - a coordinate fallback being flagged
- The eval suite contains about 15 tasks across Quiet Hours and one open-source app, split into about 10 development tasks and 5 held-out tasks. Grow it only after the first full sweep shows the run time is affordable.
- Each task contains acceptance criteria, a good build, at least one proof-bug build with its expected failing checkpoint, and at least one held-out bug build.
- Development sweeps use three clean reruns per test and are labeled provisional. Published numbers use the full ten.
- Quiet Hours scheduling bugs, including incorrect end-alarm timing, are included as seeded cases.
- Eval configurations are one-shot generation with no device exploration, one-shot generation filtered by the same Verifier, an agent running Maestro MCP until green with no proof (the main baseline to beat), and the full ProofLoop loop. A trace Compiler joins as a configuration only if it gets built.
- Metrics are proof rate (share of tasks reaching `proven`), held-out bug-catch rate, flake rate, first-run pass rate, cost per accepted test, duration, policy blocks, and human edits needed.
- Catch rate on proof bugs is not reported as a result for configurations that filter on it, because accepted tests catch them by construction.
- Human edits needed is the number of lines changed in the generated test between ProofLoop's output and the merged version.
- Regression thresholds are set after the first baseline is recorded. Held-out results are run only for marked releases.
- There is no prior art in this repository. The fixture design should be established with the first end-to-end Quiet Hours flow.

## Out of Scope

- iOS, physical device farms, and cross-platform testing.
- Building a new device-control or MCP automation layer.
- A custom trace Compiler, until evals justify it.
- A hosted product with its own device fleet, dashboard, or billing.
- Remote device fleets, warm-pool orchestration, and pool rotation.
- Live device streaming. Recordings provide the required evidence.
- Slack or chat interfaces and multiplayer agent sessions.
- Jira integration and a general Jira-to-PR software factory.
- Overnight autonomous bug fixing or autonomous merging.
- Generating seeded bugs automatically. Bugs are authored by hand at first.
- Compose UI test generation.
- Processing real personal or regulated health data.

## Further Notes

### Glossary

- **Acceptance criteria:** the plain-language behavior to verify.
- **Checkpoint:** an observable condition derived from an acceptance criterion.
- **Trace:** the ordered record of flows the agent ran, screens it inspected, and evidence from exploration.
- **Regression test:** the deterministic Maestro flow saved from exploration.
- **Good build:** the app build expected to satisfy the criteria.
- **Seeded-bug build:** a build with a known, deliberate defect.
- **Proof bug:** a seeded bug tied to an expected failing checkpoint and used to accept or reject a test.
- **Held-out bug:** a seeded bug the loop never uses, run after the verdict to measure catch rate.
- **Device-state probe:** a fixed, read-only query of system state used to assert a checkpoint the UI does not show.
- **Proof:** repeated passes on the good build plus expected-checkpoint failures on proof-bug builds.
- **Run record:** the versioned result of one ProofLoop run.

### Delivery phases

1. **Weeks 1-2:** one Quiet Hours flow end to end, with clean snapshots and live log observation. Build the proof gate first so it works on a hand-written flow, then add agent authoring. Start with a UI-only flow (create a schedule and see it listed). Then spike the time-dependent flow: controlled clock, do-not-disturb permission, a device-state probe, and Maestro failure-to-checkpoint mapping.
2. **Weeks 3-4:** seeded bugs, eval tasks, baselines, and the CI gate.
3. **Week 5:** guardrails, failure labels, before-and-after recordings, tracing, repair, and packaging. If this phase runs long, cut repair first, then tracing.
4. **Week 6:** architecture decision records, the "what failed" writeup, results table, and a two-minute demo.

### Portfolio result to fill in

"Built open-source proof gate that turns acceptance criteria into deterministic Android tests; proved tests for [P]% of [N] tasks, and those tests caught [X]% of held-out bugs vs [Y]% for one-shot generation, at $[C] per test."

Replace the placeholders only with measured results.

### Risks

- ProofLoop is a working name, and availability has not been checked.
- Emulator differences can create noise, so host and system image must be recorded with results.
- Hand-authored seeded bugs may favor ProofLoop. Held-out bugs, held-out tasks, and public fixtures reduce this risk, and the writeup should state it plainly.
- Normal use requires someone to supply seeded-bug builds, which most teams do not have. This is the main adoption gap, and the writeup should say so. Using the commit before a feature as its broken build is an untested way to reduce it.
- Maestro MCP plus a short script may match the full loop. If the phase-one bake-off shows that, ship ProofLoop as a Claude Code skill and a small runner instead of the full architecture.
- A full sweep is hundreds of clean-snapshot emulator runs. Measure the time for one task in phase one before committing to the suite size.
