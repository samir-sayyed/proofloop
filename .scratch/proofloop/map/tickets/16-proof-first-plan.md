# Test author and build order

**Type:** grilling
**Assignee:** user
**Blocked by:** None
**Status:** closed

## Question

Should ProofLoop keep mobile-mcp plus a trace Compiler, or use Maestro MCP as the test author and build the proof gate first?

## Resolution

Proof gate first, with Claude Code and Maestro MCP as the author. The Verifier must work on a hand-written flow. The Allowlist becomes a check on each flow. The trace Compiler is built only if evals show Maestro MCP authoring loses. The main eval baseline is an agent running Maestro MCP until green. Evidence: https://claude.ai/artifact/YD4hBfJSejQVXXxAVqDmgv
