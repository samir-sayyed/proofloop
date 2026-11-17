# Sunflower tasks

Second app for the eval suite: [android/sunflower](https://github.com/android/sunflower), Apache-2.0,
cloned (depth 1, commit 2a357a3) to `.scratch/oss/sunflower`.

Planned criterion: adding a plant to the garden lists it on the "My garden" tab with today's planting date.

Seeded bugs (patches here, written against 2a357a3):
- `bug-garden-wrong-column` (proof): the My garden subquery selects the planting's own `id` instead of
  `plant_id`, so the garden stays empty after adding a plant. Must fail at C2.
  (A first attempt, `NOT IN`, crashed the app at launch; the proof gate correctly refused to count a crash.)
- `bug-date-day-of-year` (held-out): date format `MMM D` (day of year) instead of `MMM d`, so the
  planting date reads "Nov 322, 2026" on 18 Nov 2026.

Reproduce it (building runs the cloned project's Gradle scripts, which is third-party code: read them first):

```bash
git clone https://github.com/android/sunflower .scratch/oss/sunflower && git -C .scratch/oss/sunflower checkout 2a357a3
tasks/sunflower/build-apks.sh
proofloop prove tasks/sunflower/garden-planting/task.json
```

Result: proven, 10/10 clean runs, both bugs caught ([record](../../docs/results/sunflower-garden-planting.record.json)).
