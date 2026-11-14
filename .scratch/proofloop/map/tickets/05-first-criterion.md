# Quiet Hours first criterion, bug and expected checkpoint

**Type:** grilling
**Assignee:** samirsayyed
**Blocked by:** None
**Status:** closed

## Question

Which exact acceptance criterion is proven first (proposed: a schedule fires its end alarm at the configured end time)? Which seeded bug breaks it, and which checkpoint must fail? Do the good and bug APKs already exist?

## Resolution

App: `~/Desktop/quiet-hours` (com.sam.quiethours, 5.3.2, Compose). Good build is a debug APK from a tagged commit (`proofloop/good-5.3.2`); each seeded bug is a branch `proofloop/bug-<name>` from that tag, written by the user from a proposed change. The app stays unmodified: locators are text and content description, locale pinned to English.

**Criterion 1 (proven first, UI-only):** creating a "Weekdays" schedule 22:00-07:00 and activating it shows it on Home with its title, "Weekdays", and the correct "Next:" time. Clock pinned to a fixed moment (e.g. a Wednesday 12:00).
- C1 wizard opens from "Add Schedule"
- C2 after "Activate", title is listed on Home
- C3 day summary reads "Weekdays"
- C4 status reads "Next:" with the right day and time
- Proof bug: Weekdays preset off by one (saves Tue-Sat), must fail at C3.
- Held-out bug: next-start calculation skips today's occurrence, should fail at C4.

**Criterion 2 (time-dependent spike):** a Silent schedule restores normal sound at its end time.
- E1 30 s before end: status "Active until ..." and ringer silent
- E2 within 60 s after end: ringer normal and status "Next: ..."
- Ringer read by a read-only device-state probe outside the agent.
- Proof bug: end fires one hour late (DST-style end-delay error), must fail at E2.
- Held-out bug: end fires 5 minutes early, should fail at E1.

Constraint found in code: the app's backup alarm (QuietPeriodGuard) restores sound 2 minutes after the expected end if the END alarm is lost, computed independently. E2's window must stay under 2 minutes or the backup masks late-end bugs.

Secret hygiene: the app repo root has an untracked `openrouterapikey` file; it must never enter a commit or ProofLoop evidence.
