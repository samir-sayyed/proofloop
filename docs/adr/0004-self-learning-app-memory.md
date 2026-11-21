# App memory learns from good-build runs, behind a gated write path

Status: accepted, 2026-11-21

## Context

The app map (`app-map.md`) halved authoring time, and a map that an author updated by hand passed a
learned fact on: three later authors avoided a failure that three authors without it all hit
([experiments/quiet-hours-loop](../../experiments/quiet-hours-loop/README.md)). But the update depended on the
agent choosing to write it down. The talk this came from (askui, next app devCon 2026) builds the map from the
agent's own runs.

Where the learning signal is matters. The fact that transferred ("Next start" and the end-sound sentence are one
text element, so the exact text is not found) appeared only in an author's *failed* trial run. Proof runs execute
only the final, passing flow, so a learner that reads proof records alone never sees it.

Two constraints are specific to a proof gate:

- **Bug builds must never feed memory.** A fact learned from a bug run ("'Weekdays' not visible after Next")
  would leak the seeded bug to the author and fit the test to it.
- **Learned text must never become an anchor.** Anchors exempt a wait from the checkpoint rule. Promoting
  state-dependent text (a plant name on My garden) would allow the exact trap that hid the bug in 6 of 6 trials.

## Decision

Memory is a write-manage-read loop beside the map, not inside it:

- **Write (observe).** `proofloop try TASK` runs a task once on the good build, keeps the attempt, and learns from
  it; authors use it instead of bare `maestro test`. `proofloop prove` learns from the good runs of each proof
  (`--no-learn` to skip). `proofloop learn` imports proofs, kept attempts, or earlier Maestro sessions
  (`~/.maestro/tests`). Bug-build runs are never read; a source labelled as a bug build is refused.
- **Extract.** From Maestro's per-command log: *edges* (one tap between two screens recognised by human anchors),
  *routes* (several taps between them), *locator fixes* (a visibility check that failed on exact text X and later
  passed with a pattern matching X, across attempts), *slow waits* (half the timeout or more) and *flaky steps*
  (failed on some good runs of one proof).
- **Manage (gate).** Every fact keeps its sources and builds. It is a candidate until re-observed (two runs; for a
  locator fix, the fixed form passing twice), contradicted if the exact text later passes, and stale if the newest
  build showed its screen without it. Routes are examples, never stale.
- **Read.** `learned.md` is generated beside `app-map.md` (confirmed, then candidates, stale, contradicted). The
  skill reads it after the map. It never writes anchors or map prose; a person promotes a fact into the map.

Not built: the talk's per-screen loading at each step (authors read the whole map, which is small), learning
harness facts (driver timeouts, full storage, downgrade installs; they are runner lessons, not app facts), and
generating tests for unvisited screens.

## Consequences

- Facts arrive without an agent choosing to record them, with evidence attached, and go stale when the app moves on.
- Screen recognition is only as good as the human anchors. On Sunflower the anchor "My garden" is also a tab label
  on the plant list, so the learner recorded a wrong edge and re-observation "confirmed" it: recurrence proves
  consistency, not truth. Anchor quality is now the main lever.
- Authoring attempts must go through `try` (or be imported) to be learned from.
