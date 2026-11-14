# Build tickets: status after v0.1 (2026-11-14)

The architecture changed during the work (docs/adr/0001, 0002): Claude Code with Maestro MCP authors flows,
and a stdlib Python runner proves them. Ticket titles below are the original plan; status lines say what shipped.

Done: run seam, fixture and environment manager, flow allowlist, plan approval gate, agent authoring (skill),
flow checker, verifier, first end-to-end proof, report and PR publisher, failure labeler (rule-based),
seeded bugs and task format, eval runner, repair (skill step), packaging, docs.

Not done:
- 10: injected-instruction test screen (defense is a skill rule, not measured).
- 14: partly done: one open-source app (Sunflower, 1 task); the planned ~15-task suite and held-out task split are not built.
- 15: eval regression thresholds in CI (needs a baseline across more tasks).
- 19: trace Compiler, deferred by ADR 0001.
