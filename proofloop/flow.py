"""Flow checker: parse a Maestro flow, enforce the command allowlist, map steps to checkpoints.

Checkpoints are declared in the flow with comment markers:

    # checkpoint: C3 day summary reads Weekdays
    - assertVisible: "Weekdays"

A marker labels the assertion commands that follow it. The first non-assertion
command after those assertions ends the checkpoint, so a failing tap is never
counted as catching a bug.

ponytail: line-based parser, no YAML library. It reads top-level list items only,
which is all a flat Maestro flow has. Nested flows (runFlow) are blocked rather
than parsed; add a YAML parser if nested flows are ever allowed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ASSERTIONS = {"assertVisible", "assertNotVisible", "assertTrue", "extendedWaitUntil"}

# Commands the agent's flows may not use. Each would let a test leave the target app,
# run arbitrary code, hide flakiness, or undo the runner's environment control.
BLOCKED = {
    "runScript": "runs arbitrary JavaScript",
    "evalScript": "runs arbitrary JavaScript",
    "openLink": "can open other apps or arbitrary URLs",
    "runFlow": "nested flows hide commands from the checker",
    "retry": "retries hide flakiness the proof must measure",
    "repeat": "loops make step-to-checkpoint mapping ambiguous",
    "clearKeychain": "changes device state outside the app",
    "setLocation": "changes device state outside the runner",
    "travel": "changes device state outside the runner",
    "addMedia": "writes files to the device",
    "setAirplaneMode": "changes device state outside the runner",
    "toggleAirplaneMode": "changes device state outside the runner",
}

CHECKPOINT_RE = re.compile(r"^#\s*checkpoint:\s*([A-Za-z0-9_-]+)\s*(.*)$")
APPID_RE = re.compile(r"^appId:\s*['\"]?([\w.]+)")


@dataclass
class Command:
    index: int  # 0-based position among top-level commands
    name: str
    body: str  # full text of the command, including nested lines
    line: int  # 1-based line in the file
    checkpoint: str | None = None


@dataclass
class Flow:
    path: Path
    app_id: str | None
    commands: list[Command]
    checkpoints: dict[str, str]  # id -> description

    def checkpoint_of(self, index: int) -> str | None:
        if 0 <= index < len(self.commands):
            return self.commands[index].checkpoint
        return None


@dataclass
class CheckResult:
    errors: list[str] = field(default_factory=list)
    fallbacks: list[str] = field(default_factory=list)  # coordinate taps, flagged not blocked

    @property
    def ok(self) -> bool:
        return not self.errors


def _name(item: str) -> str:
    item = item.strip()
    return re.split(r"[:\s]", item, maxsplit=1)[0]


def parse_flow(path: str | Path) -> Flow:
    path = Path(path)
    lines = path.read_text().splitlines()
    app_id = None
    in_header = any(line.strip() == "---" for line in lines)
    commands: list[Command] = []
    checkpoints: dict[str, str] = {}
    pending: str | None = None
    current: str | None = None
    seen_assert = False

    for n, line in enumerate(lines, 1):
        if in_header:
            m = APPID_RE.match(line)
            if m:
                app_id = m.group(1)
            if line.strip() == "---":
                in_header = False
            continue
        m = CHECKPOINT_RE.match(line.strip()) if line.startswith("#") else None
        if m:
            pending = m.group(1)
            checkpoints[pending] = m.group(2).strip()
            continue
        if line.startswith("- "):
            name = _name(line[2:])
            cmd = Command(len(commands), name, line, n)
            if pending:
                current, pending, seen_assert = pending, None, False
            if name in ASSERTIONS and current:
                cmd.checkpoint = current
                seen_assert = True
            elif name not in ASSERTIONS and seen_assert:
                current, seen_assert = None, False
            commands.append(cmd)
        elif commands and line.startswith((" ", "\t")):
            commands[-1].body += "\n" + line
    return Flow(path, app_id, commands, checkpoints)


def check_flow(flow: Flow, app_id: str, anchors: frozenset[str] = frozenset()) -> CheckResult:
    """anchors: texts the app map says are always on their screen; waiting on them is setup, not state."""
    r = CheckResult()
    where = flow.path.name
    if flow.app_id != app_id:
        r.errors.append(f"{where}: appId is {flow.app_id!r}, task app is {app_id!r}")
    if not flow.commands:
        r.errors.append(f"{where}: no commands")
    for c in flow.commands:
        loc = f"{where}:{c.line}"
        if c.name in BLOCKED:
            r.errors.append(f"{loc}: blocked command {c.name} ({BLOCKED[c.name]})")
        if c.name in ("launchApp", "stopApp", "killApp"):
            other = re.search(r"appId:\s*['\"]?([\w.]+)", c.body)
            if other and other.group(1) != app_id:
                r.errors.append(f"{loc}: {c.name} targets another app {other.group(1)}")
        if c.name == "launchApp" and re.search(r"clearState:\s*true", c.body):
            r.errors.append(f"{loc}: launchApp clearState is not allowed; the runner resets app state "
                            "(launching right after a clear can let the pending task removal kill the app)")
        if c.name in ("stopApp", "killApp"):
            r.errors.append(f"{loc}: {c.name} force-stops the app, which cancels its pending alarms; not allowed")
        if c.name == "launchApp" and not re.search(r"stopApp:\s*false", c.body):
            r.errors.append(f"{loc}: launchApp must set stopApp: false "
                            "(the default force-stop cancels the app's pending alarms; the runner already reset the app)")
        if re.search(r"\bpoint:", c.body):
            r.fallbacks.append(f"{loc}: coordinate tap ({c.body.strip().splitlines()[0]})")
    for cp in flow.checkpoints:
        if not any(c.checkpoint == cp for c in flow.commands):
            r.errors.append(f"{where}: checkpoint {cp} has no assertion after its marker")
    # A wait or assertion outside any checkpoint that leads straight into one (no action between)
    # observes the same screen state: on a bug build it fails as "setup" and hides the checkpoint.
    # All 6 fresh authors in experiments/map-effect made this mistake.
    cmds = flow.commands
    for i, c in enumerate(cmds):
        if c.checkpoint or c.name not in ASSERTIONS:
            continue
        texts = re.findall(r'"([^"]+)"', c.body)
        if texts and all(t in anchors for t in texts):
            continue  # waiting for a screen anchor (from the app map) is setup
        j = i + 1
        while j < len(cmds) and not cmds[j].checkpoint and cmds[j].name in ASSERTIONS:
            j += 1
        if j < len(cmds) and cmds[j].checkpoint:
            r.errors.append(f"{where}:{c.line}: {c.name} right before checkpoint {cmds[j].checkpoint} is outside it; "
                            f"move the '# checkpoint: {cmds[j].checkpoint}' marker above it (a bug that breaks this "
                            "state would fail at setup and not count), or, if it waits for text that is always on "
                            "that screen, list the text as an anchor in the app map")
    return r


def check_task_flows(task) -> tuple[CheckResult, dict[str, Flow]]:
    """Check every flow in a task, and that each expected checkpoint exists somewhere."""
    total = CheckResult()
    flows: dict[str, Flow] = {}
    anchors: frozenset[str] = frozenset()
    map_path = task.dir.parent / "app-map.md"  # tasks/<app>/app-map.md
    if map_path.exists():
        from .appmap import load
        anchors = frozenset(a for s in load(map_path).screens.values() for a in s.anchors)
    for p in task.flow_paths():
        f = parse_flow(p)
        flows[str(p)] = f
        r = check_flow(f, task.app_id, anchors)
        total.errors += r.errors
        total.fallbacks += r.fallbacks
    declared = {cp for f in flows.values() for cp in f.checkpoints} | set(task.probe_checkpoints())
    for b in task.bugs:
        if b.expect and b.expect not in declared:
            total.errors.append(f"bug {b.name} expects checkpoint {b.expect}, which no flow or probe declares")
    return total, flows
