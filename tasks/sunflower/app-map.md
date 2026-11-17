# App map: Sunflower
app: com.google.samples.apps.sunflower
> Made with the app-map skill on 2026-11-17: good build (commit 2a357a3), Pixel 8 emulator,
> Android 14, fresh data, clock pinned to Wed 18 Nov 2026 10:00 (`proofloop prepare garden-planting`).

## screen: garden
anchors: "My garden", "Plant list"
- tap "Add plant" -> plant_list
- tap "Plant list" -> plant_list
- tap "Planted" -> plant_detail
- back -> exit
- precondition: launch screen; with fresh data it reads "Your garden is empty" with an "Add plant" button
- rule: each planted plant shows its name, "Planted" with the date ("Nov 18, 2026"), and "Last Watered" ("water in 3 days.")
- hazard: "Your garden is empty" and "Add plant" are only there when the garden is empty; wait on "Plant list" instead

## screen: plant_list
anchors: "Plant list", "Filter by grow zone"
- tap "Avocado" -> plant_detail
- tap "Filter by grow zone" -> plant_list
- tap "My garden" -> garden
- precondition: the list is seeded from assets by a background worker on first launch; wait for a plant name before tapping
- rule: 17 plants alphabetically (Apple, Avocado, Beet, ...); "Filter by grow zone" toggles to grow zone 9 only (Avocado, Grape, Orange, Tomato)

## screen: plant_detail
anchors: "Watering needs", "Navigate up"
- tap "Add plant" -> plant_detail
- tap "Navigate up" -> plant_list
- back -> plant_list
- tap "Share" -> ? (not taken: sends to another app)
- rule: shows "Watering needs" and "every N days" (Avocado: every 3 days)
- rule: "Add plant" adds the plant to the garden and disappears; a planted plant's detail has no "Add plant"
- hazard: the description ends with a "(from Wikipedia)" link that opens the browser; do not tap the text
- lookup: the planting date is not here; it is on the garden card

## route: plant-a-plant
1. garden: tap "Plant list"
2. plant_list: wait for "Avocado", tap "Avocado"
3. plant_detail: tap "Add plant", tap "Navigate up"
4. plant_list: tap "My garden"
5. garden: "Planted" shows on each planted card (a state to assert in a checkpoint, not a setup wait)
