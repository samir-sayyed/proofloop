# Map: ProofLoop phase-1 decisions

Label: wayfinder:map

## Destination

A decision log that clears every design question blocking phase 1, so nothing is left to decide before building the first Quiet Hours end-to-end flow (weeks 1-2). Decisions only, no build work. Build plan lives in ../issues/.

## Notes

- Source of truth for the design: /Users/samirsayyed/Desktop/proofloop/SPEC.md. Use its glossary (checkpoint, trace, run record, good build, seeded-bug build, proof).
- Quiet Hours is the user's own app with source available; good and seeded-bug APKs are built by the user.
- Phase 1 only: macOS local host, Maestro MCP as device backend and test author, Maestro output, Python + Claude Agent SDK.
- Tracker: local markdown. Tickets in tickets/NN-slug.md; claim = set `Assignee:`; blocking via `Blocked by:`. Research findings in research/.

## Decisions so far

- [mobile-mcp: is its trace rich enough to compile?](tickets/02-mobile-mcp-trace.md): element list suffices for locators, but no trace is kept and no allowlist exists. Superseded as phase-1 backend by Test author and build order.
- [Maestro: what it can and cannot do](tickets/01-maestro-capabilities.md): works on APK without source; cannot control clock or call adb, so time is set between flows (one flow per checkpoint segment); failing step maps to checkpoint via commands.json.
- [ARTEMIS as exploration baseline](tickets/03-artemis-baseline.md): optional external comparison only; a small adapter can read its SQLite store, re-deriving locators from the stored hierarchy.
- [Test author and build order](tickets/16-proof-first-plan.md): proof gate first, Claude Code with Maestro MCP as author; trace Compiler only if evals justify it.
- [Quiet Hours first criterion, bug and expected checkpoint](tickets/05-first-criterion.md): prove UI-only "Weekdays schedule listed" first (bug fails day summary), then end-alarm restore with a 60 s window under the app's 2-minute backup alarm.
- [Tag the good build and write the four bug branches](tickets/17-good-build-and-bug-branches.md): five APKs built; the weekdays bug fails at C3 on device; the app's own unit tests miss both criterion-1 bugs and catch both criterion-2 bugs.
- [Skill and runner, or full architecture?](tickets/11-script-ceiling.md): skill plus a small stdlib Python runner; the runner owns everything deterministic.
- [Emulator host setup and snapshot strategy](tickets/04-emulator-host-setup.md): app-data reset with a wait for the old task, not snapshots.
- [Trace and run-record shape](tickets/06-run-record-shape.md): versioned run record in proofloop/verify.py.
- [Controlled time and device pinning strategy](tickets/07-time-and-pinning.md): pin clock and time zone without root; time steps live in the task, not the flow.
- [Checkpoint-plan format and observability rule](tickets/08-plan-format.md): checkpoint markers in flows plus probe checkpoints.
- [Which Maestro commands must the allowlist block?](tickets/12-allowlist-commands.md): implemented in proofloop/flow.py.
- [Which read-only device queries report ringer mode and DND?](tickets/18-ringer-probe.md): dumpsys audio, zen_mode, ring volume.
- [Maestro MCP bake-off](tickets/10-maestro-mcp-bakeoff.md): both criteria proven with agent-written flows.
- [Can the commit before a feature serve as its broken build?](tickets/13-commit-before-feature.md): yes for new or fixed behaviour; the pre-fix commit was caught at E1s.

## Not yet specified

- Model cost per accepted test: measured in the agent session, not by the runner.

Destination reached: nothing is left to decide before building, and v0.1 is built. Open tickets 14-15 are human tasks (engineer interviews, commercial tool trial).

## Out of scope

- [Hand-compile one trace to Maestro](tickets/09-hand-compile.md): the proof-first plan has no trace Compiler in phase 1.
- Phases 2-4: evals, OSS apps, CI gate, repair, injection defense, failure labeler, packaging, docs (build plan in ../issues/).
- Project name availability check: not phase-1 blocking, but must be done before publishing.
