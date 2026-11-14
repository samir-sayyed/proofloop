# Which Maestro commands must the allowlist block?

**Type:** research
**Assignee:** agent
**Blocked by:** None
**Status:** closed

## Question

Which Maestro YAML commands can run scripts, open other apps or arbitrary links, or change device state? Can a proxy sit in front of Maestro MCP's run tool and see each flow, including nested runFlow and JavaScript? What does the agent need to keep?

## Resolution

Implemented in proofloop/flow.py: blocked runScript, evalScript, openLink, runFlow, retry, repeat, clearKeychain, setLocation, travel, addMedia, airplane mode; other app ids; clearState, stopApp, killApp, and launchApp without stopApp: false. Coordinate taps are flagged, not blocked. Nested flows are blocked rather than parsed.
