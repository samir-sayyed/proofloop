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

import json
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path

PROBE_STATES = ("quiet", "normal")
ROLES = ("proof", "held_out")


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

    @property
    def dir(self) -> Path:
        return self.path.parent

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
    )
