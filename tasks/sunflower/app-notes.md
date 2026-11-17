# Sunflower: notes for the author

Facts about the good build only. Read before exploring; append what you learn after proving.
Never put bug details here (the author must not see them).

## Screens
- Tabs: "My garden", "Plant list". "Plant list" is on screen in every state.
- Plant detail: add-to-garden button; planted plants show in "My garden" with watering info.

## Rules and gotchas
- Setup waits should target "Plant list", not "Your garden is empty" (state-dependent).
- Date text is locale-formatted ("Nov 18, 2026"); pin the clock and read it from the app.
- The Premium screen can be reached by stray taps; use text locators, not coordinates.
