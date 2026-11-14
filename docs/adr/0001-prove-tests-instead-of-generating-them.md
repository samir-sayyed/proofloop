# Prove agent-written tests instead of building a test generator

Status: accepted, 2026-11-10

## Context

The original spec planned an agent that explores the app through mobile-mcp, records a trace, and a
custom Compiler that turns the trace into a Maestro test. Research before building found that Maestro
already ships an MCP server: a coding agent can inspect the screen, run inline YAML, and save a
deterministic flow that replays with no model. Callstack's agent-device also exports Maestro YAML from
an agent run. None of the tools found checks that a generated test fails when the feature breaks.

## Decision

Use Claude Code with Maestro MCP as the test author. Build the proof gate: repeated clean runs on the
good build, plus seeded-bug builds that must fail at a declared checkpoint. Defer the trace Compiler
until an eval shows Maestro MCP authoring losing on proof rate, held-out catch rate, or flake rate.

## Consequences

- One device stack (Maestro) instead of two, and no element-reference mapping problem.
- ProofLoop's value is the proof, not the authoring; the main eval baseline becomes "agent runs Maestro
  until green", which is much harder to beat than one-shot generation.
- The Verifier must accept any Maestro flow, including hand-written ones.
