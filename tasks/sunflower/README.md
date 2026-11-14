# Sunflower tasks (not built yet)

Second app for the eval suite: [android/sunflower](https://github.com/android/sunflower), Apache-2.0,
cloned (depth 1, commit 2a357a3) to `.scratch/oss/sunflower`.

Planned criterion: adding a plant to the garden lists it on the "My garden" tab with today's planting date.

Seeded bugs (patches here, written against 2a357a3):
- `bug-garden-wrong-column` (proof): the My garden subquery selects the planting's own `id` instead of
  `plant_id`, so the garden stays empty after adding a plant. Must fail at C2.
  (A first attempt, `NOT IN`, crashed the app at launch; the proof gate correctly refused to count a crash.)
- `bug-date-day-of-year` (held-out): date format `MMM D` (day of year) instead of `MMM d`, so the
  planting date reads "Nov 322, 2026" on 18 Nov 2026.

Not done: building it runs the cloned project's Gradle scripts (third-party code), which needs the
owner's go-ahead. Then: `build-apks.sh`, explore with Maestro, write `flow.yaml` and `task.json`, prove.
