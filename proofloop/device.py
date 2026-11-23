"""Environment manager and device-state probe, over adb. No root needed.

Everything the agent must not do lives here and runs outside the agent's tools:
installs, clearing app data, permission grants, clock and time zone, sound probes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import datetime, time as clock_time
from zoneinfo import ZoneInfo


class DeviceError(RuntimeError):
    """The device or host could not be put in the required state. Not a test result."""


def _adb_path() -> str:
    for cand in (shutil.which("adb"), os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),
                 os.path.join(os.environ.get("ANDROID_HOME", ""), "platform-tools", "adb")):
        if cand and os.path.isfile(cand):
            return cand
    raise DeviceError("adb not found (install platform-tools or set ANDROID_HOME)")


class AdbDevice:
    MIN_FREE_MB = 100  # floor; install() scales the requirement with APK size

    def __init__(self, serial: str | None = None):
        self.adb = _adb_path()
        self.serial = serial or self._only_device()
        self.tz: ZoneInfo | None = None
        self.date = None  # pinned date for set_clock / wait_clock

    def _only_device(self) -> str:
        out = subprocess.run([self.adb, "devices"], capture_output=True, text=True).stdout
        serials = [l.split()[0] for l in out.splitlines()[1:] if l.strip().endswith("device")]
        if len(serials) != 1:
            raise DeviceError(f"need exactly one connected device or --device, found {serials or 'none'}")
        return serials[0]

    def sh(self, *args: str, check: bool = True, timeout: float = 60) -> str:
        r = subprocess.run([self.adb, "-s", self.serial, "shell", *args],
                           capture_output=True, text=True, timeout=timeout)
        if check and r.returncode != 0:
            raise DeviceError(f"adb shell {' '.join(args)} failed: {(r.stderr or r.stdout).strip()}")
        return r.stdout.replace("\r", "")

    # --- host and device facts, recorded with every result ---
    def facts(self) -> dict:
        prop = lambda k: self.sh("getprop", k, check=False).strip()
        return {"serial": self.serial, "model": prop("ro.product.model"), "android": prop("ro.build.version.release"),
                "image": prop("ro.build.fingerprint"), "host": os.uname().sysname + " " + os.uname().machine}

    def free_mb(self) -> int:
        line = self.sh("df", "-k", "/data", check=False).strip().splitlines()[-1].split()
        try:
            return int(line[3]) // 1024
        except (IndexError, ValueError):
            return -1

    # --- environment control ---
    def free_automation_lock(self) -> None:
        """mobile-mcp's on-device server holds the only UiAutomation connection and blocks Maestro."""
        for line in self.sh("ps", "-A", "-o", "PID,ARGS", check=False).splitlines():
            if "mobilecli" in line and "DeviceServer" in line:
                self.sh("kill", line.split()[0], check=False)

    def install(self, apk) -> None:
        if not os.path.isfile(apk):
            raise DeviceError(f"APK not found: {apk}")
        need = max(self.MIN_FREE_MB, int(os.path.getsize(apk) / 2**20 * 2.5))  # old + new copy + dex
        free = self.free_mb()
        if 0 <= free < need:
            self.sh("pm", "trim-caches", "4G", check=False)
            free = self.free_mb()
            if 0 <= free < need:
                raise DeviceError(f"device has {free} MB free on /data; need about {need} MB to install {os.path.basename(str(apk))}")
        # -d: an older build (a seeded-bug build, or the commit before a fix) can be installed over a newer one
        r = subprocess.run([self.adb, "-s", self.serial, "install", "-r", "-d", str(apk)],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0 or "Success" not in r.stdout:
            raise DeviceError(f"install {os.path.basename(str(apk))} failed: {(r.stderr or r.stdout).strip()}")

    def reset(self, app_id: str, grants: list[str], dnd_access: bool) -> None:
        """Clear app data, then wait until the old task is gone before anything launches it.

        Launching while the clear-data task removal is still pending lets that removal kill
        the new process: a blank screen and "failed to attach" ~1 run in 7 without this wait.
        """
        self.sh("pm", "clear", app_id)
        deadline = time.monotonic() + 10
        while f"{app_id}/" in self.sh("dumpsys", "activity", "activities", check=False):
            if time.monotonic() > deadline:
                raise DeviceError(f"{app_id} task still present 10 s after clearing data")
            time.sleep(0.25)
        time.sleep(0.5)
        for g in grants:
            self.sh("pm", "grant", app_id, g)
        if dnd_access:
            self.sh("cmd", "notification", "allow_dnd", app_id)

    def pin_clock(self, when: datetime, tz: str) -> None:
        self.tz = ZoneInfo(tz)
        self.date = when.date()
        self.sh("settings", "put", "global", "auto_time", "0")
        self.sh("settings", "put", "global", "auto_time_zone", "0")
        self.sh("cmd", "alarm", "set-timezone", tz)
        self._set(when)

    def set_clock(self, at: clock_time) -> None:
        if self.date is None:
            raise DeviceError("set_clock before pin_clock")
        self._set(datetime.combine(self.date, at))

    def _set(self, when: datetime) -> None:
        ms = int(when.replace(tzinfo=self.tz).timestamp() * 1000)
        self.sh("cmd", "alarm", "set-time", str(ms))

    def now(self) -> datetime:
        epoch = int(self.sh("date", "+%s").strip())
        return datetime.fromtimestamp(epoch, self.tz).replace(tzinfo=None)

    def wait_clock(self, at: clock_time, timeout_s: float = 600) -> None:
        target = datetime.combine(self.date, at)
        deadline = time.monotonic() + timeout_s
        while self.now() < target:
            if time.monotonic() > deadline:
                raise DeviceError(f"device clock did not reach {at} within {timeout_s:.0f} s")
            time.sleep(0.5)

    def restore_clock(self) -> None:
        self.sh("settings", "put", "global", "auto_time", "1", check=False)
        self.sh("settings", "put", "global", "auto_time_zone", "1", check=False)

    def load_snapshot(self, name: str, timeout_s: float = 180) -> None:
        """Load an emulator snapshot, then wait for the system to be ready. Emulators only."""
        if not self.serial.startswith("emulator-"):
            raise DeviceError(f"--snapshot needs an emulator; {self.serial} is not one")
        r = subprocess.run([self.adb, "-s", self.serial, "emu", "avd", "snapshot", "load", name],
                           capture_output=True, text=True, timeout=timeout_s)
        if r.returncode != 0 or "KO" in r.stdout:
            raise DeviceError(f"loading snapshot {name} failed: {(r.stdout + r.stderr).strip()}")
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                if self.sh("getprop", "sys.boot_completed", check=False, timeout=10).strip() == "1" and \
                        "package:" in self.sh("pm", "path", "android", check=False, timeout=10):
                    return
            except subprocess.TimeoutExpired:
                pass
            if time.monotonic() > deadline:
                raise DeviceError(f"{self.serial} not ready {timeout_s:.0f} s after loading snapshot {name}")
            time.sleep(1)

    # --- evidence: a screen recording of one good run, for reviewers ---
    REC = "/sdcard/proofloop-run.mp4"

    def start_recording(self) -> None:
        self.sh("rm", "-f", self.REC, check=False)
        self._rec = subprocess.Popen([self.adb, "-s", self.serial, "shell", "screenrecord", "--time-limit", "180",
                                      "--bit-rate", "2000000", self.REC],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop_recording(self, dest) -> str | None:
        """Stop the recording and pull it to dest. Returns the path, or None if there is no video."""
        rec, self._rec = getattr(self, "_rec", None), None
        if rec is None:
            return None
        self.sh("pkill", "-INT", "screenrecord", check=False)  # SIGINT lets screenrecord finish the mp4
        try:
            rec.wait(timeout=10)
        except subprocess.TimeoutExpired:
            rec.kill()
        time.sleep(1)
        r = subprocess.run([self.adb, "-s", self.serial, "pull", self.REC, str(dest)], capture_output=True, text=True)
        self.sh("rm", "-f", self.REC, check=False)
        return str(dest) if r.returncode == 0 and os.path.isfile(dest) and os.path.getsize(dest) > 0 else None

    # --- read-only probe ---
    def probe(self) -> dict:
        audio = self.sh("dumpsys", "audio", check=False)
        ringer = next((l.split("=")[-1].strip() for l in audio.splitlines() if "mode (internal)" in l), "?")
        zen = self.sh("settings", "get", "global", "zen_mode", check=False).strip()
        ring = self.sh("settings", "get", "system", "volume_ring_speaker", check=False).strip()
        quiet = ringer != "NORMAL" or zen != "0" or ring == "0"
        return {"time": self.now().strftime("%H:%M:%S") if self.tz else "", "ringer": ringer,
                "zen": zen, "ring": ring, "state": "quiet" if quiet else "normal"}
