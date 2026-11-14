# mobile-mcp: is its trace rich enough to compile?

**Type:** research
**Assignee:** research subagent
**Blocked by:** None
**Status:** closed

## Question

Do mobile-mcp's element lists, refs and actions capture enough per step (resource id, text, bounds, UI state before/after) to compile a deterministic Maestro test? Does it expose screen recording and logs? What is missing?

## Resolution

Partly. The element list (type, text, label, identifier, rect, states) is rich enough to pick locators, but mobile-mcp keeps no trace: the Device boundary must record per step the tool and args, timestamp, resolved element, and before/after dumps. Refs are session-local and cannot appear in tests. No allowlist exists, so the boundary must proxy a fixed subset. Continuous adb logcat capture is needed for live logs. Several items UNVERIFIED pending a live emulator spike. Full detail: research/02-mobile-mcp-trace.md

Superseded in part by Test author and build order: mobile-mcp is no longer the phase-1 device backend.
