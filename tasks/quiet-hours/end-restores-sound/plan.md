# Plan: end-restores-sound

Criterion: a Silent schedule restores normal sound at its end time, and Home shows it active during the window
and the next start after it.

Checkpoints (sound probes read by the runner; status checks are visible UI text):
- S the phone goes quiet when the 9:00 window starts (probe, polled until 09:00:25)
- E1 the phone is still quiet 30 seconds before the 17:00 end (probe)
- E1s Home shows the schedule as active during the window
- E2 normal sound is restored at the end time (probe, polled until 17:01:00)
- E2s Home shows the next start after the end

Draft written on 2026-11-23 from the flow markers and probe steps. The plan was originally approved in chat
("samirsayyed, 2026-11-14, first-criterion grilling, E1-E2; status checks added by agent") with no plan file.
S, E1s and E2s were added by the agent, so review them in particular, then run
`proofloop approve tasks/quiet-hours/end-restores-sound/task.json --by NAME`.
