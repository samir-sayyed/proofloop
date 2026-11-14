# 03: Device boundary: flow allowlist over Maestro MCP

**What to build:** The agent's only path to the device: a proxy over Maestro MCP, or a recorded fake. Each flow is parsed and checked against an allowed command set before it runs, what ran is recorded, blocked flows land in the run record, and screen or log text is treated as untrusted.

**Blocked by:** 01

**Status:** done (v0.1)

- [ ] Commands that leave the target app or run scripts are rejected in code
- [ ] Cloud tools and app install or removal are not exposed to the agent
- [ ] Blocked-action scenario passes through the Run seam
- [ ] Real backend and recorded fake share one interface
