# Can the commit before a feature serve as its broken build?

**Type:** task
**Assignee:** agent
**Blocked by:** 10-maestro-mcp-bakeoff
**Status:** closed

## Question

On one real Quiet Hours change, does the test for the new feature fail on the previous commit at the expected checkpoint, or does it fail too early to count? Record what kinds of change this works for.

## Resolution

Yes, for a change whose test asserts the new behaviour. Quiet Hours e4ba3eb fixed the stale Home status line; its parent 72587d5 was added to the end-alarm task as a proof bug expected at E1s, with no hand-written bug. Result: proven 10/10, and 72587d5 failed exactly at E1s ("Active until 5:00 PM" not visible). Record: docs/results/quiet-hours-end-restores-sound.record.json (final eval) and docs/results/earlier/quiet-hours-end-restores-sound.with-prefix.record.json. Limit: it only works when the test checks what the change added; it cannot stand in for bugs in existing behaviour.
