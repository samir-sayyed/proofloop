# App map: Quiet Hours
app: com.sam.quiethours
> Made with the app-map skill on 2026-11-17: good build e4ba3eb, Pixel 8 emulator, Android 14,
> fresh data, clock pinned to Wed 18 Nov 2026 08:00 (`proofloop prepare weekdays-listed`).
> Not explored yet: schedule card details, Templates "Edit"/"Use", drawer items, Settings.

## screen: welcome
anchors: "Get Started", "Never miss a moment of peace"
- tap "Get Started" -> routine_picker
- precondition: shown only with fresh app data (first launch)

## screen: routine_picker
anchors: "What brings you to Quiet Hours?", "Explore App"
- tap "Explore App" -> trial
- tap "Continue" -> routine_picker
- rule: "Continue" needs at least one routine selected ("Please select at least one option to continue"); "Explore App" skips the choice

## screen: trial
anchors: "Your 3-day Premium trial", "No payment details. No automatic charge."
- tap "Continue" -> home
- tap "See lifetime Premium" -> ? (not taken: purchase screen)
- hazard: stray taps here can reach the Premium purchase screen; use text locators only

## screen: home
anchors: "Manage your sound profiles", "Add Schedule"
- tap "Add Schedule" -> wizard_details
- tap "Templates" -> templates
- tap "Meetings" -> meetings
- tap "Menu" -> drawer
- tap "Fix" -> ? (not taken: opens device battery settings)
- back -> exit
- rule: with no schedules it reads "Your sound schedules will appear here" with "Browse Templates" and "Create Schedule"
- rule: each schedule card shows its title, day summary ("Weekdays"), "• 8h •" and a status line ("Next: Today 9:00 AM", "Active until 5:00 PM", "Next: Tomorrow 9:00 AM")
- rule: the status line text is read from the app, never guessed ("Today", not the weekday name)
- hazard: "Review battery limits on this device" banner is always there on the emulator; it is not an error
- lookup: sound state is not on screen; the runner's probe steps read do-not-disturb and ring volume

## screen: wizard_details
anchors: "Step 1 of 2", "Schedule Details"
- input "Schedule Title" -> wizard_details
- tap "Weekdays" -> wizard_details
- tap "Next" -> wizard_review
- tap "Back" -> home
- rule: "Next" does nothing until a title is typed
- rule: day presets "Daily", "Weekdays", "Weekends" or single days Sun-Sat; default time range 9:00 AM-5:00 PM ("8h")
- rule: "Quick Start Templates" (Focus Time, Gym Time, Reading Time) pre-fill the form

## screen: wizard_review
anchors: "Step 2 of 2", "Activate"
- tap "Activate" -> saved
- tap "Back" -> wizard_details
- tap "Preview Notification" -> ? (not taken: posts a notification)
- rule: shows title, "Repeating", days, start sound "Ring 0% · Music 0% · Notification 0%" and end sound "Ring 70% · Music 80% · Notification 70%"

## screen: saved
anchors: "Routine saved", "Done"
- tap "Done" -> home
- rule: states the next start ("Next start: Wed, Nov 18, 9:00 AM") and when end settings apply (5:00 PM)
- rule: the next start and the end-settings sentence are one text element ("Next start: Wed, Nov 18, 9:00 AM" then a newline and "End sound settings apply at 5:00 PM after that start. Check Home for routine status.")
- rule: a text locator for the whole element must continue past the start line, e.g. "Next start: Wed, Nov 18, 9:00 AM.*"; the exact start line alone is not found by assertVisible

## screen: templates
anchors: "Schedule Templates", "Built-in Templates"
- tap "Back" -> home
- rule: built-in Focus Time (5 days), Gym Time (3 days), Reading Time (2 days), Sleep Mode, each with "Edit" and "Use"

## screen: meetings
anchors: "No Meeting Schedules", "Setup Calendar"
- tap "Home" -> home
- tap "Setup Calendar" -> ? (not taken: asks for calendar permission)
- back -> exit

## screen: drawer
anchors: "Manage your device volumes", "Close navigation menu"
- tap "Close navigation menu" -> home
- tap "Premium" -> ? (not taken: purchase screen)
- rule: items Home, VIP Calls, Theme, Meetings Setup, Settings, Premium ("3 days left in trial")

## route: add-weekday-schedule
1. welcome: tap "Get Started"
2. routine_picker: tap "Explore App"
3. trial: tap "Continue"
4. home: wait for "Manage your sound profiles", tap "Add Schedule"
5. wizard_details: tap "Schedule Title", type "Smoke", hide keyboard, tap "Weekdays", tap "Next"
6. wizard_review: tap "Activate"
7. saved: tap "Done"
8. home: the card shows "Smoke", "Weekdays", "Next: Today 9:00 AM"
