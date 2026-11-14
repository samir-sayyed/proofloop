# Checkpoint-plan format and observability rule

**Type:** grilling
**Assignee:** agent
**Blocked by:** 05-first-criterion
**Status:** closed

## Question

What is the structured checkpoint plan schema (including the seeded bug each checkpoint should catch), and what rule decides a criterion is not observable through the UI?

## Resolution

Checkpoints are comment markers in the flow ('# checkpoint: C3 description') labelling the assertions that follow; probe checkpoints are task steps. A proof bug declares the checkpoint it must fail ('expect'). Observability rule: a checkpoint must be visible UI text or controls, or a supported device-state probe; otherwise the skill stops and reports it.
