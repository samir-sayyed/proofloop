# Bind the proof to its artifacts and the approval to its plan; run proof bugs early

Status: accepted, 2026-11-23

## Context

Three gaps showed up when comparing ProofLoop with AI Engineer 2026 talks on software factories (Korlam on CI
for agent-scale commits, Tížková on Factory's validators, Knox on running cheap checks first):

1. The record stored APK and flow *paths*, not their contents. A flow edited after its proof could still be
   published as "proven".
2. `approved_by` was free text. Nothing tied it to what was approved, so a repair could add, drop or reword a
   checkpoint, and "never weaken an assertion" was only a skill rule.
3. The runner did all good runs before any bug build. Missing a proof bug was the most common rejection
   (6 of 6 in map-effect round 1), and each one cost 10 good runs before the miss was found.

## Decision

- **Artifacts.** `prove` records a sha256 of the task file, `plan.md`, every flow and every APK
  (`record.artifacts`, record schema 2). `publish` refuses a record without hashes and any flow whose current
  hash differs.
- **Approval.** The human approves `plan.md`, which is still written before any flow exists, by running
  `proofloop approve TASK --by NAME`. This writes `approved_by` and `approved_plan` (the plan's sha256). `prove` returns
  `needs_human` if `plan.md` changed since then, or if the checkpoint ids declared in the flows and probes are
  not exactly the plan's ids. `check` reports the approval state as a warning but does not fail on it, so CI
  stays a flow check.
- **Order.** One good run, then each proof bug, then the remaining good runs (skipped if a proof bug was
  missed), then held-out bugs. A good-build failure still takes precedence (`rejected_flaky`).

## Consequences

- The approval covers *which* checkpoints exist, not the exact assertion text inside each. A repair can still
  change a locator (for example adding `.*` for multi-line text). The proof bugs, not the approval, guard
  whether that assertion still catches the defect. Binding assertion text too was considered and rejected: it
  would need a re-approval on every locator repair.
- Plan ids are read as the first word of each bullet in `plan.md` when it contains a digit (C1) or names a
  declared checkpoint (a probe called S). Prose bullets are ignored.
- The four checked-in tasks need a human `proofloop approve` before they can be proven again. Two of them
  (weekdays-listed, end-restores-sound) had no `plan.md`, so drafts were written from their flow markers for
  review.
- The bug list in `task.json` is not covered by the approval. A repair could move a proof bug's `expect`, or
  turn it into `held_out` (held-out bugs never affect the verdict), without invalidating the approval. The
  artifact hash of `task.json` records that it changed, but nothing refuses it yet. Folding each proof bug's
  name, role and expect into the approval hash is the obvious next step.
- The remaining good runs are skipped only when good run 1 passed and a proof bug was missed. After a
  good-build failure all runs still happen, because the labeller needs them to tell a flake from a real bug.
- The experiment scoring scripts (`experiments/*/score-trial.sh`) write a `task.json` with only `approved_by`,
  and their authors choose their own checkpoint ids, so they now score `needs_human`. They were not changed:
  generating and approving a plan from whatever the author wrote would defeat the gate. Re-running them needs
  a decision about what the experimenter's standing approval should cover.
- A rejected record now has fewer good runs, so its flake bound covers fewer runs. Proven records are unchanged.
