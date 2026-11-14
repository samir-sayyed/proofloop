# Ship as a Claude Code skill plus a small deterministic runner

Status: accepted, 2026-11-14

## Context

The spec listed ten modules (Planner, Explorer, Device boundary, Compiler, Verifier, Repair,
Environment manager, Failure labeler, Evidence publisher, Eval runner) on the Claude Agent SDK. The
bake-off then proved both Quiet Hours criteria with agent-written Maestro flows and about 100 lines of
shell. Every hard problem it hit (a reset race, force-stop cancelling alarms, an unpinned clock, a sound
probe) was solved in the runner, none in an agent.

## Decision

- Planning, exploring, writing flows, and repair are steps of a Claude Code skill, run in the user's
  agent session with Maestro MCP.
- Everything that must be deterministic is a Python package with no third-party dependencies: flow
  checker, environment manager, probes, verifier, run record, report, publisher, eval runner, and a
  rule-based failure labeler.
- The human plan approval is enforced in code: `prove` refuses a task without `approved_by`.

## Consequences

- No API keys or model calls inside ProofLoop itself; model cost is the agent session's, so the
  runner does not measure it.
- Agent topology, model tiers per role, and a model-based failure labeler are not built. They can be
  added if evals show a measurable benefit.
- The flow parser is line-based because flat Maestro flows are simple lists and nested flows are blocked.
