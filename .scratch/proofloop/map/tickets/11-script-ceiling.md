# Skill and runner, or full architecture?

**Type:** grilling
**Assignee:** samirsayyed
**Blocked by:** 10-maestro-mcp-bakeoff
**Status:** closed

## Question

If Maestro MCP plus a short script matches the bake-off result, should ProofLoop ship as a Claude Code skill and small runner? Which modules in SPEC.md survive that decision?

## Resolution

Ship ProofLoop as a Claude Code skill plus a small deterministic Python runner (standard library only). The skill does planning and authoring with Maestro MCP; the runner owns reset, clock, probes, repeated runs, checkpoint mapping, verdict, run record and report. Evidence: the bake-off proved both Quiet Hours criteria with agent-written flows and about 100 lines of shell, and every hard problem (reset race, force-stop cancelling alarms, clock pinning, sound probe) was solved in the runner, not in an agent. Spec modules that survive: Planner and Explorer as skill steps, Flow checker, Verifier, Environment manager, run record, report/PR publisher, eval runner, failure labeler (rule-based first). Decided by the agent under the user's instruction to take the best decisions.
