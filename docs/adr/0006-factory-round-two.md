# Feed the gate, keep its evidence, and measure it: round two from the software-factory research

Status: accepted, 2026-11-23

## Context

ADR 0005 bound proofs to their artifacts and approvals to `plan.md`, from AI Engineer 2026 software-factory
talks (Korlam, Tížková, Knox, Pocock and others; summarized in the owner's brain wiki,
`wiki/concepts/software-factory.md`). It left gaps: the bug list was outside the approval, experiment scoring
broke, nothing re-proved a test when the app changed, all but one bug was hand-written, and cost was
unmeasured. This round closes those gaps and checks each change against real runs.

## Decision

- **Approval covers the bugs.** `approved_bugs` hashes each bug's name, role and expected checkpoint. Moving an
  `expect` or turning a proof bug into a held-out bug needs a new approval. Rebuilding an APK does not.
- **The checker refuses what cannot fail, and fixes what has one answer.** A checkpoint that only repeats text
  already checked with no action in between is rejected. `check --fix` applies the `launchApp` and
  marker-above-wait fixes in code.
- **Anchors shared between screens are reported** (`proofloop map`) and ignored by the learner. They still
  exempt waits in the checker: a wait on them cannot hide a bug. A stricter checker rule was tried and
  reverted, because in round 3 of `experiments/map-effect` it added checker rounds and caught no bugs.
- **Evidence and cost in the record.** Good run 1 is screen-recorded. The task's `author` session gives peak
  context and tokens processed, read from the transcript. The eval table shows author, context and repairs.
- **Scale and reset.** `--devices` spreads good runs 2..N over more devices. `--snapshot` loads an emulator
  snapshot first, on writable emulators only.
- **Feeding and maintaining the gate.** These are new commands:
  - `history` records every proof and the build a test stopped on.
  - `mine-bugs --after GOOD` lists real fix commits whose parent differs from the good build by the bug alone.
  - `retro` groups rejections by cause.
  - `next` ranks untested app-map rules, screens and actions.
  - `from-fix` scaffolds a regression task from a fix.
  - `publish --max-open` caps open PRs.
- **Delegated approvals are labelled.** When the owner delegates approval in chat, the agent runs
  `proofloop approve --by "agent (delegated by NAME ...)"`, so the record never presents it as a human review.

## Evidence (2026-11-23, Pixel 8 image, Android 14, macOS arm64)

- **`check --fix`:** a Sunflower flow with round 1's mistake (marker below its wait, bare `launchApp`) was
  fixed in code and proven 3/3, with the bug caught at C2.
- **Two devices:** 10 good runs took 200 s, against 282 s on one device. Both runs were proven 10/10.
- **History:** all three Quiet Hours tests broke on the app's `main` (`b41de64`, 31 commits later). Each was
  0/10, because one-time tip bubbles (app PR #76) dim Home. `retro` names this `broken_setup`.
- **The repair:** optional taps on "Skip|Got it", without the app repo's `runFlow` version, which the
  allowlist blocks. With it, end-restores-sound and weekdays-listed were proven 10/10 again. next-start needed
  a second dismissal for a wizard tip that appeared only on some runs (4/10 before).
- **Mined bugs:** the parent of `2123448`, a VIP Do Not Disturb fix, was not caught by end-restores-sound. No
  test exercises VIP calls, which is a real gap. A first mined candidate was caught for the wrong reason: it
  predated the good build and lacked an older fix. That is why `--after` exists.
- **Authors** (Sunflower, 3 trials per arm): one-shot Sonnet with the map and checker but no device was 3/3
  proven, about 21 s each. Haiku with the device was 3/3 proven, about 3 min each. See
  `experiments/map-effect`, round 3.

## Consequences

- Tasks now point at the app's current build and carry two repairs each. Their history starts on 2026-11-23,
  because earlier proofs predate the history file.
- Video files and evidence stay out of git. Only `publish --with-video` copies one next to a flow.
- `--snapshot` and `-read-only` multi-instance emulators do not mix. Use a writable emulator for snapshot
  resets, or read-only copies booted from the snapshot for parallel runs.
- Samples stay small and single-app. The one-shot result says the app map carries most of the knowledge for a
  mapped flow, not that devices are unnecessary.
