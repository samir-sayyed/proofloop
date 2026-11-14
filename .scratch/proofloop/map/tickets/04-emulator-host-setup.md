# Emulator host setup and snapshot strategy

**Type:** task
**Assignee:** agent
**Blocked by:** None
**Status:** closed

## Question

Provision the local macOS emulator: pick AVD image, create a clean snapshot, confirm restore speed and that Maestro MCP can drive it. Record image, host, and snapshot commands as facts later tickets depend on. HITL checklist if the agent cannot do it alone.

## Resolution

Pixel_8_API_34 (Android 14, sdk_gphone64_arm64) on macOS. Clean state is not a snapshot restore: the runner clears app data and waits for the old task to go (ADR 0003), which proved reliable (0 hangs in 40 launches). Facts: ../../bakeoff/RESULTS.md, ../bugs/README.md.
