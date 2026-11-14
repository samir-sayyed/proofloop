# Trace and run-record shape

**Type:** grilling
**Assignee:** agent
**Blocked by:** None
**Status:** closed

## Question

What does the trace hold now that the agent works through Maestro MCP (flows run, screens inspected, blocked flows), and which fields does the versioned run record need so the Verifier, PR publisher, failure labeler and eval reports can use it as sole input? How do Maestro's commands.json and failure artifacts map into it?

## Resolution

Implemented as the versioned run record in proofloop/verify.py (schema_version 1): verdict, reason, approval, flow check (errors, coordinate fallbacks), repairs, good runs with failing checkpoint, step, error, evidence directory and probes, per-bug results, environment facts, duration, failure label. Maestro's commands.json maps failures to flow commands by index.
