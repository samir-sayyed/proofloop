# ARTEMIS as exploration baseline

**Type:** research
**Assignee:** research subagent
**Blocked by:** None
**Status:** closed

## Question

Does ARTEMIS expose enough step-level action and UI-state detail to produce a compilable trace, or only a high-level result? Is it usable as an exploration baseline later?

## Resolution

Usable only as an optional external comparison, not as the device backend. ARTEMIS stores rich per-step data in its SQLite trace store (action, tap point, hierarchy before/after, recording), so a small adapter could read it and ProofLoop could compile and verify from there. Fidelity caveats: element attribution was wrong in 2 of 3 sampled steps (re-derive locators from the stored hierarchy), resource IDs were empty for Quiet Hours, and there is no allowlist, clean snapshot, or explicit waits. Not resolved: Pro-profile traces, cost per run, structured MCP result. Full detail: research/03-artemis-baseline.md

Superseded in part by Test author and build order: mobile-mcp is no longer the phase-1 device backend.
