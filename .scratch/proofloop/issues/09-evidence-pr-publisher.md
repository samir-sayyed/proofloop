# 09: Evidence and PR publisher

**What to build:** For proven runs only, opens a PR with the test, verdict, flake rate, bugs caught, cost, duration, coordinate fallbacks and before/after recordings. Failed runs get a report and no normal PR. Never merges.

**Blocked by:** 08

**Status:** done (v0.1)

- [ ] Run record is the sole input
- [ ] No credentials in traces, reports or PRs
- [ ] Failed run produces a useful report
