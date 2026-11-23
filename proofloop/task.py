"""Task file: what to prove, against which builds, on what device state.

A task is a JSON file. Paths inside it are relative to the file. Example:

{
  "name": "quiet-hours/weekdays-listed",
  "criterion": "A Weekdays schedule appears on Home with its title, days and next start.",
  "app_id": "com.sam.quiethours",
  "good": "../../apks/good.apk",
  "bugs": [
    {"name": "weekdays-off-by-one", "apk": "...", "role": "proof", "expect": "C3"},
    {"name": "next-skips-today", "apk": "...", "role": "held_out"}
  ],
  "device": {"timezone": "Asia/Kolkata", "clock": "2026-11-18T08:00:00",
             "grants": ["android.permission.POST_NOTIFICATIONS"], "dnd_access": false},
  "approved_by": "who approved the checkpoint plan, and when",
  "approved_plan": "sha256 of plan.md at approval (written by `proofloop approve`)",
  "good_runs": 10,
  "budget_minutes": 60,
  "steps": [
    {"flow": "flow.yaml"},
    {"set_clock": "16:59:15"},
    {"wait_clock": "16:59:30"},
    {"probe": {"checkpoint": "E1", "expect": "quiet"}},
    {"probe": {"checkpoint": "E2", "expect": "normal", "until": "17:01:00"}}
  ],
  "repairs": [{"reason": "...", "change": "..."}]
}

Step kinds:
  flow        run a Maestro flow; failures map to "# checkpoint: X" markers in it
  set_clock   set the device clock to HH:MM:SS on the pinned date
  wait_clock  wait until the device clock reaches HH:MM:SS
  probe       read device sound state; "until" polls up to that clock time
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path

PROBE_STATES = ("quiet", "normal")
ROLES = ("proof", "held_out")
# A checkpoint line in plan.md starts with its id: "- C1 the wizard opens", "- A2: ...", "- **E1s** ...".
PLAN_LINE_RE = re.compile(r"^\s*[-*]\s+\**([A-Za-z][A-Za-z0-9_-]*)\**(?=[\s:.)]|$)")


def file_sha256(path) -> str | None:
    """sha256 of a file as 'sha256:<hex>', or None if it does not exist."""
    try:
        with open(path, "rb") as f:
            return "sha256:" + hashlib.file_digest(f, "sha256").hexdigest()
    except FileNotFoundError:
        return None


def bugs_digest(bugs) -> str:
    """sha256 over (name, role, expect) of every bug, order-independent. APK paths are not part of it:
    rebuilding a bug changes its file, not what the human approved it to prove."""
    rows = sorted([b[0], b[1], b[2]] for b in bugs)
    return "sha256:" + hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def plan_ids(text: str, declared: set[str] = frozenset()) -> set[str]:
    """Checkpoint ids a plan lists: a bullet's first word, if it has a digit (C1) or is a declared id (S).

    ponytail: first-word heuristic, so prose bullets ("- Note: ...") are ignored unless they name a checkpoint.
    """
    words = {m.group(1) for line in text.splitlines() if (m := PLAN_LINE_RE.match(line))}
    return {w for w in words if any(ch.isdigit() for ch in w) or w in declared}


class TaskError(ValueError):
    pass


@dataclass
class Bug:
    name: str
    apk: Path
    role: str
    expect: str | None = None


@dataclass
class DeviceSettings:
    timezone: str | None = None
    clock: datetime | None = None
    grants: list[str] = field(default_factory=list)
    dnd_access: bool = False


@dataclass
class Task:
    path: Path
    name: str
    criterion: str
    app_id: str
    good: Path
    bugs: list[Bug]
    device: DeviceSettings
    steps: list[dict]
    good_runs: int = 10
    budget_minutes: float | None = None
    repairs: list[dict] = field(default_factory=list)
    approved_by: str | None = None  # human approval of the checkpoint plan; prove refuses without it
    approved_plan: str | None = None  # sha256 of plan.md when it was approved (set by `proofloop approve`)
    approved_bugs: str | None = None  # sha256 of the bug list (name, role, expect) at approval
    author: dict = field(default_factory=dict)  # who wrote the flows: {"agent", "model", "session"}

    @property
    def dir(self) -> Path:
        return self.path.parent

    @property
    def plan_path(self) -> Path:
        return self.dir / "plan.md"

    def approval_problem(self, declared: set[str]) -> str | None:
        """Why the approval does not cover what will run, or None. declared: checkpoint ids in flows and probes."""
        if not self.approved_by:
            return "the checkpoint plan has no approval (a human reviews plan.md, then runs proofloop approve TASK --by NAME)"
        if not self.approved_plan:
            return "the approval is not bound to plan.md (a human reviews plan.md, then runs proofloop approve TASK --by NAME)"
        actual = file_sha256(self.plan_path)
        if actual is None:
            return "plan.md is missing; the approval has nothing to cover"
        if actual != self.approved_plan:
            return "plan.md changed since it was approved; a human must review it and approve again"
        if not self.approved_bugs:
            return "the approval does not cover the bug list (approve again: proofloop approve TASK --by NAME)"
        if bugs_digest([(b.name, b.role, b.expect) for b in self.bugs]) != self.approved_bugs:
            return ("the bugs changed since approval (a name, role or expected checkpoint); "
                    "a human must approve again")
        planned = plan_ids(self.plan_path.read_text(), declared)
        extra, missing = sorted(declared - planned), sorted(planned - declared)
        if extra or missing:
            parts = ([f"not in the approved plan: {', '.join(extra)}"] if extra else []) + \
                    ([f"in the plan but not in any flow or probe: {', '.join(missing)}"] if missing else [])
            return "the flows do not match the approved plan's checkpoints (" + "; ".join(parts) + ")"
        return None

    def flow_paths(self) -> list[Path]:
        return [self.dir / s["flow"] for s in self.steps if "flow" in s]

    def probe_checkpoints(self) -> list[str]:
        return [s["probe"]["checkpoint"] for s in self.steps if "probe" in s]


def _clock(value: str, where: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError as e:
        raise TaskError(f"{where}: {value!r} is not HH:MM:SS") from e


def load_task(path: str | Path) -> Task:
    path = Path(path).resolve()
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise TaskError(f"cannot read task {path}: {e}") from e

    def need(key):
        if key not in raw:
            raise TaskError(f"{path.name}: missing {key!r}")
        return raw[key]

    base = path.parent
    bugs = []
    for b in raw.get("bugs", []):
        role = b.get("role", "proof")
        if role not in ROLES:
            raise TaskError(f"bug {b.get('name')}: role must be one of {ROLES}")
        if role == "proof" and not b.get("expect"):
            raise TaskError(f"proof bug {b.get('name')}: needs 'expect' (the checkpoint that must fail)")
        bugs.append(Bug(b["name"], (base / b["apk"]).resolve(), role, b.get("expect")))
    if not any(b.role == "proof" for b in bugs):
        raise TaskError(f"{path.name}: at least one proof bug is required")

    d = raw.get("device", {})
    device = DeviceSettings(
        timezone=d.get("timezone"),
        clock=datetime.fromisoformat(d["clock"]) if d.get("clock") else None,
        grants=list(d.get("grants", [])),
        dnd_access=bool(d.get("dnd_access", False)),
    )

    steps = need("steps")
    if not steps:
        raise TaskError(f"{path.name}: no steps")
    for i, s in enumerate(steps):
        where = f"step {i + 1}"
        if len(s) != 1:
            raise TaskError(f"{where}: exactly one of flow, set_clock, wait_clock, probe")
        kind, value = next(iter(s.items()))
        if kind == "flow":
            if not (base / value).is_file():
                raise TaskError(f"{where}: flow file {value} not found")
        elif kind in ("set_clock", "wait_clock"):
            if device.clock is None:
                raise TaskError(f"{where}: {kind} needs device.clock (the pinned date)")
            _clock(value, where)
        elif kind == "probe":
            if value.get("expect") not in PROBE_STATES or not value.get("checkpoint"):
                raise TaskError(f"{where}: probe needs checkpoint and expect in {PROBE_STATES}")
            if "until" in value:
                _clock(value["until"], where)
        else:
            raise TaskError(f"{where}: unknown step {kind!r}")

    runs = int(raw.get("good_runs", 10))
    if runs < 1:
        raise TaskError("good_runs must be at least 1")

    return Task(
        path=path,
        name=need("name"),
        criterion=need("criterion"),
        app_id=need("app_id"),
        good=(base / need("good")).resolve(),
        bugs=bugs,
        device=device,
        steps=steps,
        good_runs=runs,
        budget_minutes=raw.get("budget_minutes"),
        repairs=list(raw.get("repairs", [])),
        approved_by=raw.get("approved_by"),
        approved_plan=raw.get("approved_plan"),
        approved_bugs=raw.get("approved_bugs"),
        author=dict(raw.get("author", {})),
    )


def approve(task_path: str | Path, by: str, today: str) -> str:
    """Bind a human's approval to the current plan.md: write approved_by and approved_plan into task.json.

    Reads the JSON directly, so it works before the flows exist.
    """
    task_path = Path(task_path).resolve()
    plan = task_path.parent / "plan.md"
    digest = file_sha256(plan)
    if digest is None:
        raise TaskError(f"no plan.md next to {task_path.name}; write the checkpoint plan first")
    raw = json.loads(task_path.read_text())
    # ids without a digit (a probe named S) count when a probe or an existing flow declares them
    from .flow import parse_flow
    declared = {s["probe"]["checkpoint"] for s in raw.get("steps", []) if "probe" in s}
    for s in raw.get("steps", []):
        if "flow" in s and (task_path.parent / s["flow"]).is_file():
            declared |= set(parse_flow(task_path.parent / s["flow"]).checkpoints)
    ids = plan_ids(plan.read_text(), declared)
    if not ids:
        raise TaskError("plan.md lists no checkpoints (lines like '- C1 the wizard opens')")
    bugs = [(b["name"], b.get("role", "proof"), b.get("expect")) for b in raw.get("bugs", [])]
    raw["approved_by"] = f"{by}, {today}"
    raw["approved_plan"] = digest
    raw["approved_bugs"] = bugs_digest(bugs)
    task_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
    proof = ", ".join(f"{n}@{e}" for n, r, e in bugs if r == "proof") or "none"
    return f"approved plan.md ({', '.join(sorted(ids))}; {digest[:19]}) and proof bugs ({proof}) by {by}"
