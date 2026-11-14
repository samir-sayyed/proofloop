# Maestro: what it can and cannot do

**Type:** research
**Assignee:** research subagent
**Blocked by:** None
**Status:** closed

## Question

Against a compiled APK with no app source: which locators does Maestro support (resource id, text, index), how do waits and assertions work, can it point-tap by coordinate, and can it control or mock the device clock? What does a failure report expose (failing step, usable to identify the failing checkpoint)?

## Resolution

Maestro works on a compiled APK with no app source. Locators: id (resource-id, regex), text (matches contentDescription too), index. Waits: assertVisible/assertNotVisible retry ~7s; extendedWaitUntil with timeout. Point-tap: pixels or percentages, flag as fragile, prefer percentage. Clock: Maestro cannot set or mock it and flows cannot call adb, so the environment manager must set time between flows; implies one flow per checkpoint segment. Failure reports (junit, commands.json with step sequence numbers, screenshot, hierarchy, logs) let plain code map the failing step to a checkpoint and tell crashes from wrong-checkpoint failures. Maestro adb hangs must be labeled blocked_environment. Several items UNVERIFIED (id full-match, DND permission grant, default extendedWaitUntil timeout, mid-flow clock jump). Full detail: research/01-maestro-capabilities.md
