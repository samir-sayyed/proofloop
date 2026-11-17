"""Fast tests through the public seam: task file in, run record out. Fake device and fake Maestro."""

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from proofloop.device import DeviceError
from proofloop.evals import table
from proofloop.flow import check_flow, parse_flow
from proofloop.maestro import FlowResult, parse_commands
from proofloop.report import publish, render
from proofloop.task import TaskError, load_task
import proofloop.verify
from proofloop.verify import flake_upper_bound, prove

proofloop.verify.POLL_S = 0
_ROOT = tempfile.TemporaryDirectory()


def tearDownModule():
    _ROOT.cleanup()

FLOW = """appId: com.example.app
---
- launchApp:
    stopApp: false
- tapOn: "Add"
# checkpoint: C1 form opens
- assertVisible: "Form"
- tapOn: "Save"
# checkpoint: C2 item listed
- assertVisible: "Item"
# checkpoint: C3 status shown
- assertVisible: "Next: Today"
"""
# top-level command indexes: 0 launchApp, 1 tapOn Add, 2 assert C1, 3 tapOn Save, 4 assert C2, 5 assert C3


class FakeDevice:
    """Simulated device: a clock, an installed build, and a sound state decided by a script."""

    def __init__(self, sound=None, fail_install=None):
        self.build = None
        self.clock = datetime(2026, 1, 1)
        self.sound = sound or (lambda build, now: "normal")
        self.fail_install = fail_install
        self.calls = []
        self.serial = "fake"
        self.date = None

    def free_automation_lock(self): self.calls.append("unlock")
    def facts(self): return {"model": "Fake", "android": "14", "host": "test"}
    def install(self, apk):
        if self.fail_install and self.fail_install in str(apk):
            raise DeviceError("install failed: no space")
        self.build = Path(apk).stem
        self.calls.append(f"install {self.build}")
    def reset(self, app_id, grants, dnd): self.calls.append("reset")
    def pin_clock(self, when, tz): self.clock, self.date = when, when.date()
    def set_clock(self, at): self.clock = datetime.combine(self.date, at)
    def wait_clock(self, at): self.clock = max(self.clock, datetime.combine(self.date, at))
    def now(self):
        self.clock += timedelta(seconds=1)  # time passes on every read
        return self.clock
    def probe(self): return {"state": self.sound(self.build, self.now())}
    def restore_clock(self): self.calls.append("restore_clock")


class FakeMaestro:
    """outcomes(build, flow_name, call_number) -> FlowResult."""

    def __init__(self, device, outcomes=None):
        self.device = device
        self.outcomes = outcomes or (lambda b, f, n: FlowResult(True))
        self.count = {}

    def run(self, flow, out_dir):
        key = (self.device.build, flow.name)
        self.count[key] = self.count.get(key, 0) + 1
        return self.outcomes(self.device.build, flow.name, self.count[key])


def fails_at(index, error="Assertion is false"):
    return FlowResult(False, failed_index=index, error=error)


class TaskDir:
    def __init__(self, flow=FLOW, **overrides):
        d = Path(tempfile.mkdtemp(dir=_ROOT.name))
        (d / "flow.yaml").write_text(flow)
        for name in ("good", "bug-proof", "bug-held"):
            (d / f"{name}.apk").write_text("apk")
        task = {
            "name": "example/item-listed", "criterion": "An added item is listed.", "app_id": "com.example.app",
            "good": "good.apk",
            "bugs": [{"name": "proof", "apk": "bug-proof.apk", "role": "proof", "expect": "C2"},
                     {"name": "held", "apk": "bug-held.apk", "role": "held_out"}],
            "device": {"clock": "2026-11-18T08:00:00", "timezone": "UTC"},
            "good_runs": 10, "steps": [{"flow": "flow.yaml"}], "approved_by": "tester",
        }
        task.update(overrides)
        (d / "task.json").write_text(json.dumps(task))
        self.path = d / "task.json"
        self.dir = d

    def prove(self, device, outcomes=None, **kw):
        return prove(load_task(self.path), device, FakeMaestro(device, outcomes), self.dir / "out", **kw)


def by_build(good=None, proof=None, held=None):
    table_ = {"good": good, "bug-proof": proof, "bug-held": held}
    def outcomes(build, flow, n):
        o = table_.get(build)
        return o(n) if callable(o) else (o or FlowResult(True))
    return outcomes


class ProveVerdicts(unittest.TestCase):
    def test_proven_when_good_passes_and_proof_bug_fails_at_expected_checkpoint(self):
        t = TaskDir()
        rec = t.prove(FakeDevice(), by_build(proof=fails_at(4), held=fails_at(5)))
        self.assertEqual(rec["verdict"], "proven")
        self.assertEqual(rec["good"]["passes"], 10)
        self.assertAlmostEqual(rec["good"]["flake_upper_bound_95"], 0.259, places=3)
        held = [b for b in rec["bugs"] if b["role"] == "held_out"][0]
        self.assertTrue(held["caught"])
        self.assertEqual(held["result"]["checkpoint"], "C3")
        self.assertEqual(rec["failure_label"], "none")

    def test_flaky_good_build_is_rejected(self):
        t = TaskDir()
        rec = t.prove(FakeDevice(), by_build(good=lambda n: fails_at(1, "Element not found") if n == 6 else FlowResult(True),
                                             proof=fails_at(4)))
        self.assertEqual(rec["verdict"], "rejected_flaky")
        self.assertEqual(rec["good"]["passes"], 9)
        self.assertIsNone(rec["good"]["flake_upper_bound_95"])
        self.assertEqual(rec["good"]["runs"][5]["checkpoint"], "setup")
        self.assertEqual(rec["failure_label"], "flaky")

    def test_proof_bug_that_passes_is_a_miss(self):
        rec = TaskDir().prove(FakeDevice())
        self.assertEqual(rec["verdict"], "rejected_missed_bug")
        self.assertIn("proof passed", rec["reason"])

    def test_failure_at_wrong_checkpoint_does_not_count(self):
        rec = TaskDir().prove(FakeDevice(), by_build(proof=fails_at(2)))
        self.assertEqual(rec["verdict"], "rejected_missed_bug")
        self.assertIn("failed at C1, expected C2", rec["reason"])

    def test_failure_on_an_action_between_checkpoints_does_not_count(self):
        rec = TaskDir().prove(FakeDevice(), by_build(proof=fails_at(3, "Element not found: Save")))
        self.assertEqual(rec["verdict"], "rejected_missed_bug")
        self.assertEqual(rec["bugs"][0]["result"]["checkpoint"], "action")

    def test_environment_failure_blocks_without_judging_the_test(self):
        rec = TaskDir().prove(FakeDevice(), by_build(good=FlowResult(False, error="driver did not start", environment=True)))
        self.assertEqual(rec["verdict"], "blocked_environment")
        self.assertEqual(rec["failure_label"], "environment")

    def test_install_failure_blocks_and_clock_is_restored(self):
        d = FakeDevice(fail_install="bug-proof")
        rec = TaskDir().prove(d, by_build(proof=fails_at(4)))
        self.assertEqual(rec["verdict"], "blocked_environment")
        self.assertIn("no space", rec["reason"])
        self.assertEqual(d.calls[-1], "restore_clock")
        self.assertIn("install good", d.calls[-2])

    def test_budget_exhausted(self):
        rec = TaskDir(budget_minutes=0).prove(FakeDevice())
        self.assertEqual(rec["verdict"], "budget_exhausted")

    def test_fail_fast_stops_good_runs(self):
        rec = TaskDir().prove(FakeDevice(), by_build(good=fails_at(5), proof=fails_at(4)), fail_fast=True)
        self.assertEqual(len(rec["good"]["runs"]), 1)
        self.assertEqual(rec["verdict"], "rejected_flaky")
        self.assertEqual(rec["failure_label"], "real_bug_in_good_build")


class ApprovalGate(unittest.TestCase):
    def test_unapproved_plan_never_reaches_the_device(self):
        device = FakeDevice()
        rec = TaskDir(approved_by=None).prove(device)
        self.assertEqual(rec["verdict"], "needs_human")
        self.assertIn("approval", rec["reason"])
        self.assertEqual(device.calls, [])


class FlowPolicy(unittest.TestCase):
    def check(self, flow):
        t = TaskDir(flow=flow)
        device = FakeDevice()
        rec = t.prove(device)
        return rec, device

    def test_blocked_command_is_policy_and_never_touches_the_device(self):
        rec, device = self.check(FLOW + '- runScript: "steal.js"\n')
        self.assertEqual(rec["verdict"], "blocked_policy")
        self.assertIn("runScript", rec["reason"])
        self.assertEqual(device.calls, [])

    def test_other_app_and_force_stop_and_clear_state_are_blocked(self):
        for extra, word in [('- launchApp:\n    appId: com.other.app\n    stopApp: false\n', "another app"),
                            ('- stopApp\n', "force-stops"),
                            ('- launchApp:\n    clearState: true\n    stopApp: false\n', "clearState"),
                            ('- launchApp\n', "stopApp: false"),
                            ('- openLink: "https://example.com"\n', "openLink")]:
            with self.subTest(word=word):
                rec, _ = self.check(FLOW + extra)
                self.assertEqual(rec["verdict"], "blocked_policy", rec["reason"])
                self.assertIn(word, rec["reason"])

    def test_checkpoint_without_assertion_needs_a_human(self):
        rec, _ = self.check(FLOW + "# checkpoint: C9 nothing checks this\n- tapOn: \"Done\"\n")
        self.assertEqual(rec["verdict"], "needs_human")

    def test_expected_checkpoint_must_exist(self):
        t = TaskDir(bugs=[{"name": "proof", "apk": "bug-proof.apk", "role": "proof", "expect": "C7"}])
        rec = t.prove(FakeDevice())
        self.assertEqual(rec["verdict"], "needs_human")
        self.assertIn("C7", rec["reason"])

    def test_coordinate_fallback_is_flagged_not_blocked(self):
        rec, _ = self.check(FLOW.replace('- tapOn: "Save"', '- tapOn:\n    point: "50%,90%"'))
        self.assertEqual(len(rec["flow_check"]["coordinate_fallbacks"]), 1)
        self.assertIn("Coordinate fallbacks:** 1", render(rec))

    def test_checkpoint_mapping(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.yaml"
            p.write_text(FLOW)
            f = parse_flow(p)
            self.assertEqual([c.checkpoint for c in f.commands], [None, None, "C1", None, "C2", "C3"])
            self.assertTrue(check_flow(f, "com.example.app").ok)

    def test_wait_right_before_checkpoint_is_rejected_unless_anchor(self):
        gated = ('appId: com.example.app\n---\n- launchApp:\n    stopApp: false\n- tapOn: "Garden"\n'
                 '- extendedWaitUntil:\n    visible: "{w}"\n    timeout: 5000\n'
                 '# checkpoint: C1 plant listed\n- assertVisible: "Avocado"\n')
        fixed = ('appId: com.example.app\n---\n- launchApp:\n    stopApp: false\n- tapOn: "Garden"\n'
                 '# checkpoint: C1 plant listed\n- extendedWaitUntil:\n    visible: "Avocado"\n    timeout: 5000\n'
                 '- assertVisible: "Avocado"\n')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.yaml"
            p.write_text(gated.format(w="Avocado"))
            r = check_flow(parse_flow(p), "com.example.app")
            self.assertFalse(r.ok)
            self.assertIn("right before checkpoint C1", r.errors[0])
            p.write_text(gated.format(w="My garden"))  # a screen anchor from the app map is setup
            self.assertTrue(check_flow(parse_flow(p), "com.example.app", frozenset({"My garden"})).ok)
            self.assertFalse(check_flow(parse_flow(p), "com.example.app").ok)
            p.write_text(fixed)
            self.assertTrue(check_flow(parse_flow(p), "com.example.app").ok)


PROBE_STEPS = [
    {"flow": "flow.yaml"},
    {"set_clock": "16:59:15"}, {"wait_clock": "16:59:30"},
    {"probe": {"checkpoint": "E1", "expect": "quiet"}},
    {"wait_clock": "17:00:00"},
    {"probe": {"checkpoint": "E2", "expect": "normal", "until": "17:01:00"}},
]


def sound(end_at):
    """Quiet until end_at on the pinned day; each build ends at its own time."""
    def f(build, now):
        end = now.replace(hour=end_at[build][0], minute=end_at[build][1], second=0)
        return "quiet" if now < end else "normal"
    return f


class ProbeCheckpoints(unittest.TestCase):
    def test_end_alarm_proof_with_probes(self):
        t = TaskDir(steps=PROBE_STEPS, bugs=[
            {"name": "late", "apk": "bug-proof.apk", "role": "proof", "expect": "E2"},
            {"name": "early", "apk": "bug-held.apk", "role": "held_out"}])
        device = FakeDevice(sound=sound({"good": (17, 0), "bug-proof": (18, 0), "bug-held": (16, 55)}))
        rec = prove(load_task(t.path), device, FakeMaestro(device), t.dir / "out")
        self.assertEqual(rec["verdict"], "proven", rec["reason"])
        early = rec["bugs"][1]
        self.assertTrue(early["caught"])
        self.assertEqual(early["result"]["checkpoint"], "E1")

    def test_probe_names_count_as_declared_checkpoints(self):
        t = TaskDir(steps=PROBE_STEPS, bugs=[{"name": "late", "apk": "bug-proof.apk", "role": "proof", "expect": "E2"}])
        self.assertEqual(load_task(t.path).probe_checkpoints(), ["E1", "E2"])


class TaskValidation(unittest.TestCase):
    def test_proof_bug_needs_expected_checkpoint(self):
        with self.assertRaises(TaskError):
            load_task(TaskDir(bugs=[{"name": "p", "apk": "bug-proof.apk", "role": "proof"}]).path)

    def test_clock_steps_need_a_pinned_date(self):
        with self.assertRaises(TaskError):
            load_task(TaskDir(device={}, steps=[{"flow": "flow.yaml"}, {"set_clock": "09:00:00"}]).path)

    def test_needs_a_proof_bug(self):
        with self.assertRaises(TaskError):
            load_task(TaskDir(bugs=[{"name": "h", "apk": "bug-held.apk", "role": "held_out"}]).path)


class MaestroOutput(unittest.TestCase):
    def test_commands_json_skips_implicit_entries(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "commands.json"
            p.write_text(json.dumps([
                {"command": {"defineVariablesCommand": {}}, "metadata": {"status": "COMPLETED"}},
                {"command": {"applyConfigurationCommand": {}}, "metadata": {"status": "COMPLETED"}},
                {"command": {"launchAppCommand": {}}, "metadata": {"status": "COMPLETED"}},
                {"command": {"assertConditionCommand": {}}, "metadata": {"status": "FAILED",
                                                                        "error": {"message": '"Weekdays" is visible'}}},
            ]))
            self.assertEqual(parse_commands(p), (1, '"Weekdays" is visible'))

    def test_flake_bound(self):
        self.assertAlmostEqual(flake_upper_bound(59, 59), 0.0495, places=3)
        self.assertIsNone(flake_upper_bound(9, 10))


class Publishing(unittest.TestCase):
    def test_unproven_record_is_never_published(self):
        t = TaskDir()
        rec = t.prove(FakeDevice())  # missed bug
        p = t.dir / "record.json"
        p.write_text(json.dumps(rec))
        with self.assertRaises(ValueError):
            publish(p, t.dir)

    def test_proven_record_is_committed_on_its_own_branch(self):
        t = TaskDir()
        rec = t.prove(FakeDevice(), by_build(proof=fails_at(4)))
        p = t.dir / "record.json"
        p.write_text(json.dumps(rec))
        with tempfile.TemporaryDirectory() as repo:
            git = lambda *a: subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True, text=True).stdout
            git("init", "-q"); git("config", "user.email", "t@example.com"); git("config", "user.name", "t")
            git("commit", "-q", "--allow-empty", "-m", "init")
            msg = publish(p, Path(repo))
            self.assertIn("not pushed", msg)
            self.assertEqual(git("branch", "--show-current").strip(), "proofloop/example-item-listed")
            files = git("show", "--name-only", "--format=").split()
            self.assertIn(".maestro/proofloop/example-item-listed/flow.yaml", files)
            self.assertIn(".maestro/proofloop/example-item-listed/proofloop-report.md", files)

    def test_results_table(self):
        rec = TaskDir().prove(FakeDevice(), by_build(proof=fails_at(4), held=fails_at(5)))
        text = table([rec], "full loop")
        self.assertIn("proof rate 1/1", text)
        self.assertIn("held-out bug-catch rate 1/1", text)


if __name__ == "__main__":
    unittest.main()
