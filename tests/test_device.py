"""AdbDevice logic with a stub shell: probe classification, reset wait, clock conversion, install space check."""

import tempfile
import unittest
from datetime import datetime, time
from pathlib import Path
from unittest import mock

from proofloop.device import AdbDevice, DeviceError

AUDIO_NORMAL = "Ringer mode: \n- mode (internal) = NORMAL\n- mode (external) = NORMAL\n"


class StubDevice(AdbDevice):
    def __init__(self, replies):
        self.serial, self.tz, self.date, self.adb = "stub", None, None, "adb"
        self.replies = replies  # list of (prefix, reply or callable)
        self.log = []

    def sh(self, *args, check=True, timeout=60):
        cmd = " ".join(args)
        self.log.append(cmd)
        for prefix, reply in self.replies:
            if cmd.startswith(prefix):
                return reply() if callable(reply) else reply
        return ""


class Probe(unittest.TestCase):
    def probe(self, audio, zen, ring):
        d = StubDevice([("dumpsys audio", audio), ("settings get global zen_mode", zen),
                        ("settings get system volume_ring_speaker", ring)])
        return d.probe()["state"]

    def test_states(self):
        self.assertEqual(self.probe(AUDIO_NORMAL, "0\n", "3\n"), "normal")
        self.assertEqual(self.probe(AUDIO_NORMAL, "1\n", "3\n"), "quiet")  # do-not-disturb
        self.assertEqual(self.probe(AUDIO_NORMAL.replace("NORMAL", "VIBRATE", 1), "0\n", "3\n"), "quiet")
        self.assertEqual(self.probe(AUDIO_NORMAL, "0\n", "0\n"), "quiet")  # ring volume zero


class Reset(unittest.TestCase):
    def test_waits_for_old_task_then_grants(self):
        seen = iter(["  com.app/.Main\n", "  com.app/.Main\n", ""])
        d = StubDevice([("dumpsys activity activities", lambda: next(seen, ""))])
        with mock.patch("proofloop.device.time.sleep"):
            d.reset("com.app", ["android.permission.POST_NOTIFICATIONS"], dnd_access=True)
        self.assertEqual(d.log[0], "pm clear com.app")
        self.assertEqual(sum(c.startswith("dumpsys activity") for c in d.log), 3)
        self.assertIn("pm grant com.app android.permission.POST_NOTIFICATIONS", d.log)
        self.assertEqual(d.log[-1], "cmd notification allow_dnd com.app")

    def test_task_that_never_goes_away_is_an_environment_failure(self):
        d = StubDevice([("dumpsys activity activities", "com.app/.Main")])
        with mock.patch("proofloop.device.time.sleep"), \
                mock.patch("proofloop.device.time.monotonic", side_effect=[0, 5, 11]):
            with self.assertRaises(DeviceError):
                d.reset("com.app", [], False)


class Clock(unittest.TestCase):
    def test_pin_and_set_use_the_pinned_zone(self):
        d = StubDevice([])
        d.pin_clock(datetime(2026, 11, 18, 8, 0), "Asia/Kolkata")
        self.assertIn("cmd alarm set-timezone Asia/Kolkata", d.log)
        self.assertEqual(d.log[-1], "cmd alarm set-time 1794969000000")  # 08:00 IST
        d.set_clock(time(16, 59, 15))
        self.assertEqual(d.log[-1], f"cmd alarm set-time {1794969000000 + (8 * 3600 + 59 * 60 + 15) * 1000}")


class InstallSpace(unittest.TestCase):
    def test_refuses_when_device_is_full(self):
        with tempfile.TemporaryDirectory() as t:
            apk = Path(t) / "a.apk"
            apk.write_bytes(b"0" * (80 * 2**20))  # 80 MB -> needs about 200 MB
            d = StubDevice([("df -k /data", "Filesystem 1K-blocks Used Available\n/dev/x 6000000 5900000 150000\n")])
            with self.assertRaises(DeviceError) as e:
                d.install(str(apk))
            self.assertIn("146 MB free", str(e.exception))  # 150000 KB
            self.assertIn("pm trim-caches 4G", d.log)

    def test_install_allows_downgrade(self):
        with tempfile.TemporaryDirectory() as t:
            apk = Path(t) / "a.apk"
            apk.write_bytes(b"0")
            d = StubDevice([("df -k /data", "Filesystem 1K-blocks Used Available\n/dev/x 6000000 1000000 5000000\n")])
            with mock.patch("proofloop.device.subprocess.run",
                            return_value=mock.Mock(returncode=0, stdout="Success", stderr="")) as run:
                d.install(str(apk))
            self.assertIn("-d", run.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
