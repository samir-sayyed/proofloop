# 04: Planner and approval gate

**What to build:** Acceptance criteria become a structured checkpoint plan. Criteria that cannot be observed through the UI or a supported device-state probe are flagged. At approval the reviewer records which checkpoint each proof bug should fail; the Planner never sees a bug. Normal runs require approval, and only checked-in approved eval fixtures bypass the gate.

**Blocked by:** 01

**Status:** done (v0.1)

- [ ] Planner output is validated structured output
- [ ] Unobservable-criterion scenario passes
- [ ] Unapproved plan blocks exploration except for approved fixtures
- [ ] Planner receives no seeded-bug build, diff, or description
