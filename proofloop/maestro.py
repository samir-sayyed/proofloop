"""Run one Maestro flow and read where it failed from Maestro's own commands.json."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Maestro adds these before the flow's own commands in commands.json.
IMPLICIT = {"defineVariablesCommand", "applyConfigurationCommand"}


@dataclass
class FlowResult:
    passed: bool
    failed_index: int | None = None  # 0-based top-level command index in the flow file
    error: str = ""
    environment: bool = False  # Maestro or device failure, not a test result
    evidence: str = ""  # directory with commands.json, screenshot, hierarchy and logcat


def parse_commands(path: Path) -> tuple[int | None, str]:
    entries = json.loads(path.read_text())
    flow_index = 0
    for e in entries:
        name = next(iter(e.get("command", {})), "")
        if name in IMPLICIT:
            continue
        meta = e.get("metadata", {})
        if meta.get("status") == "FAILED":
            err = meta.get("error") or {}
            return flow_index, (err.get("message") if isinstance(err, dict) else str(err)) or "failed"
        flow_index += 1
    return None, ""


class MaestroRunner:
    def __init__(self, serial: str, timeout_s: float = 600):
        self.bin = shutil.which("maestro")
        if not self.bin:
            raise FileNotFoundError("maestro CLI not found; install it (see README)")
        self.serial = serial
        self.timeout_s = timeout_s

    def run(self, flow: Path, out_dir: Path) -> FlowResult:
        out_dir.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, MAESTRO_CLI_NO_ANALYTICS="1", MAESTRO_CLI_ANALYSIS_NOTIFICATION_DISABLED="true")
        try:
            r = subprocess.run([self.bin, "--device", self.serial, "test", str(flow), f"--test-output-dir={out_dir}"],
                               capture_output=True, text=True, timeout=self.timeout_s, env=env)
        except subprocess.TimeoutExpired:
            return FlowResult(False, error=f"flow timed out after {self.timeout_s:.0f} s", environment=True,
                              evidence=str(out_dir))
        (out_dir / "maestro-output.txt").write_text(r.stdout + r.stderr)
        cmds = sorted(out_dir.glob("**/commands.json"))
        if r.returncode == 0:
            return FlowResult(True, evidence=str(out_dir))
        if not cmds:  # Maestro never ran the flow: driver, device or install problem
            return FlowResult(False, error=_first_error(r.stdout + r.stderr), environment=True, evidence=str(out_dir))
        idx, err = parse_commands(cmds[-1])
        if idx is None:
            return FlowResult(False, error=_first_error(r.stdout + r.stderr), environment=True, evidence=str(out_dir))
        return FlowResult(False, failed_index=idx, error=err, evidence=str(cmds[-1].parent))


def _first_error(text: str) -> str:
    for line in text.splitlines():
        if any(k in line for k in ("Exception", "Error", "error", "FAILED", "died")):
            return line.strip()[:300]
    return text.strip().splitlines()[-1][:300] if text.strip() else "maestro failed with no output"
