# Quiet Hours: notes for the author

Facts about the good build only. Read before exploring; append what you learn after proving.
Never put bug details here (the author must not see them).

## Screens
- Home: schedule list, status line ("Next: Today 9:00 AM" / "Active until 5:00 PM").
- Schedule editor: day presets (Weekdays, ...), start and end time.

## Rules and gotchas
- Status line text is read from the app, never guessed ("Next: Today 9:00 AM", not "Next: Wed ...").
- `launchApp` must use `stopApp: false`: a force-stop cancels the app's pending alarms.
- Time-dependent checks need the pinned clock (task.json `device.clock`); a weekday schedule's
  next start is Monday on a weekend whether or not today is handled correctly.
- Sound state is checked with runner `probe` steps (do-not-disturb, ring volume), not on screen.
- Default schedule is 9:00 AM-5:00 PM.
