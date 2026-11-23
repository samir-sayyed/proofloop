"""Fast tests through the public seam: task file in, run record out. Fake device and fake Maestro."""

import json
import re
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from proofloop.device import DeviceError
from proofloop.evals import table
from proofloop.flow import check_flow, fix_flow, parse_flow
from proofloop.maestro import FlowResult, parse_commands
from proofloop.report import publish, render
from proofloop.task import TaskError, approve, bugs_digest, file_sha256, load_task, plan_ids
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
    """A task folder with an approved plan.md that lists exactly the flow's and probes' checkpoints."""

    def __init__(self, flow=FLOW, plan=None, **overrides):
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
        if plan is None:
            ids = re.findall(r"^# checkpoint: (\S+)", flow, re.M) + \
                  [s["probe"]["checkpoint"] for s in task["steps"] if "probe" in s]
            plan = "# Plan\n\n" + "".join(f"- {i} something observable\n" for i in ids)
        (d / "plan.md").write_text(plan)
        task.setdefault("approved_plan", file_sha256(d / "plan.md"))
        task.setdefault("approved_bugs", bugs_digest(
            [(b["name"], b.get("role", "proof"), b.get("expect")) for b in task["bugs"]]))
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


class RunOrder(unittest.TestCase):
    def test_proof_bugs_run_after_the_first_good_run(self):
        d = FakeDevice()
        rec = TaskDir().prove(d, by_build(proof=fails_at(4)))
        self.assertEqual(rec["verdict"], "proven")
        installs = [c for c in d.calls if c.startswith("install")]
        self.assertEqual(installs, ["install good", "install bug-proof", "install good", "install bug-held", "install good"])
        self.assertEqual(len(rec["good"]["runs"]), 10)
        self.assertNotIn("skipped", rec["good"])

    def test_missed_proof_bug_skips_the_remaining_good_runs(self):
        rec = TaskDir().prove(FakeDevice(), by_build(proof=fails_at(2)))
        self.assertEqual(rec["verdict"], "rejected_missed_bug")
        self.assertEqual(len(rec["good"]["runs"]), 1)
        self.assertIn("2-10 skipped", rec["good"]["skipped"])
        self.assertIn("skipped", rec["reason"])
        self.assertIn("skipped", render(rec))
        self.assertEqual(rec["failure_label"], "missed_bug")

    def test_good_failure_still_wins_over_a_missed_bug_and_runs_all_good_runs(self):
        rec = TaskDir().prove(FakeDevice(), by_build(good=fails_at(4)))
        self.assertEqual(rec["verdict"], "rejected_flaky")
        self.assertEqual(len(rec["good"]["runs"]), 10)
        self.assertNotIn("skipped", rec["good"])
        self.assertEqual(rec["failure_label"], "real_bug_in_good_build")  # judged on 10 runs, not 1

    def test_one_flake_on_run_one_with_a_missed_bug_is_labelled_flaky(self):
        rec = TaskDir().prove(FakeDevice(), by_build(good=lambda n: fails_at(4) if n == 1 else FlowResult(True)))
        self.assertEqual(len(rec["good"]["runs"]), 10)
        self.assertEqual(rec["failure_label"], "flaky")

    def test_single_good_run_task(self):
        rec = TaskDir(good_runs=1).prove(FakeDevice(), by_build(proof=fails_at(4)))
        self.assertEqual(rec["verdict"], "proven")
        self.assertEqual(len(rec["good"]["runs"]), 1)


class ApprovalGate(unittest.TestCase):
    def test_unapproved_plan_never_reaches_the_device(self):
        device = FakeDevice()
        rec = TaskDir(approved_by=None).prove(device)
        self.assertEqual(rec["verdict"], "needs_human")
        self.assertIn("approval", rec["reason"])
        self.assertEqual(device.calls, [])

    def test_approval_not_bound_to_a_plan_needs_a_human(self):
        device = FakeDevice()
        rec = TaskDir(approved_plan=None).prove(device)
        self.assertEqual(rec["verdict"], "needs_human")
        self.assertIn("not bound to plan.md", rec["reason"])
        self.assertEqual(device.calls, [])

    def test_plan_edited_after_approval_needs_a_human(self):
        t = TaskDir()
        (t.dir / "plan.md").write_text((t.dir / "plan.md").read_text() + "- C4 one more\n")
        rec = t.prove(FakeDevice())
        self.assertEqual(rec["verdict"], "needs_human")
        self.assertIn("changed since it was approved", rec["reason"])

    def test_flow_checkpoints_must_match_the_approved_plan(self):
        dropped = "# Plan\n- C1 form opens\n- C2 item listed\n"  # the flow also declares C3
        rec = TaskDir(plan=dropped).prove(FakeDevice())
        self.assertEqual(rec["verdict"], "needs_human")
        self.assertIn("not in the approved plan: C3", rec["reason"])
        extra = dropped + "- C3 status\n- C9 never written\n"
        rec = TaskDir(plan=extra).prove(FakeDevice())
        self.assertIn("in the plan but not in any flow or probe: C9", rec["reason"])

    def test_approve_binds_the_plan_and_unblocks_prove(self):
        t = TaskDir(approved_plan=None)
        msg = approve(t.path, "Samir", "2026-11-23")
        self.assertIn("C1, C2, C3", msg)
        raw = json.loads(t.path.read_text())
        self.assertEqual(raw["approved_by"], "Samir, 2026-11-23")
        self.assertEqual(raw["approved_plan"], file_sha256(t.dir / "plan.md"))
        self.assertEqual(t.prove(FakeDevice(), by_build(proof=fails_at(4)))["verdict"], "proven")

    def test_bug_list_changes_after_approval_need_a_human(self):
        t = TaskDir()
        raw = json.loads(t.path.read_text())
        moved_expect = [dict(raw["bugs"][0], expect="C3"), raw["bugs"][1]]
        held_to_proof = [raw["bugs"][0], dict(raw["bugs"][1], role="proof", expect="C3")]
        for change in (moved_expect, held_to_proof):
            moved = dict(raw, bugs=change)
            t.path.write_text(json.dumps(moved))
            rec = t.prove(FakeDevice())
            self.assertEqual(rec["verdict"], "needs_human", change)
            self.assertIn("bugs changed since approval", rec["reason"])

    def test_rebuilt_bug_apk_keeps_the_approval(self):
        t = TaskDir()
        (t.dir / "bug-proof-v2.apk").write_text("apk2")
        raw = json.loads(t.path.read_text())
        raw["bugs"][0]["apk"] = "bug-proof-v2.apk"
        t.path.write_text(json.dumps(raw))
        self.assertIsNone(load_task(t.path).approval_problem({"C1", "C2", "C3"}))

    def test_approval_without_bug_binding_needs_a_human(self):
        rec = TaskDir(approved_bugs=None).prove(FakeDevice())
        self.assertIn("does not cover the bug list", rec["reason"])

    def test_approve_names_a_probe_id_without_a_digit(self):
        steps = [{"flow": "flow.yaml"}, {"probe": {"checkpoint": "S", "expect": "quiet"}}]
        t = TaskDir(steps=steps, approved_plan=None)
        self.assertIn("C1, C2, C3, S", approve(t.path, "Samir", "2026-11-23"))

    def test_approve_needs_a_plan_with_checkpoints(self):
        t = TaskDir(plan="# Plan\n\nNothing numbered here.\n")
        with self.assertRaises(TaskError):
            approve(t.path, "Samir", "2026-11-23")
        (t.dir / "plan.md").unlink()
        with self.assertRaises(TaskError):
            approve(t.path, "Samir", "2026-11-23")

    def test_plan_id_formats(self):
        text = "- C1 the wizard opens\n- A2: saved screen\n* **E1s** status\n- Note: not a checkpoint\n  - C7) nested\n"
        self.assertEqual(plan_ids(text), {"C1", "A2", "E1s", "C7"})
        # an id without a digit (a probe named "S") counts only when a flow or probe declares it
        self.assertEqual(plan_ids("- S phone silenced\n- Note x\n", {"S"}), {"S"})


class RecordingDevice(FakeDevice):
    def __init__(self, serial="fake", **kw):
        super().__init__(**kw)
        self.serial = serial
        self.snapshots = []

    def start_recording(self): self.calls.append("rec start")
    def stop_recording(self, dest):
        self.calls.append("rec stop")
        Path(dest).write_bytes(b"mp4")
        return str(dest)
    def load_snapshot(self, name): self.snapshots.append(name)


class EvidenceAndScale(unittest.TestCase):
    def test_good_run_one_is_recorded_and_reported(self):
        d = RecordingDevice()
        rec = TaskDir().prove(d, by_build(proof=fails_at(4)))
        self.assertTrue(rec["good"]["video"].endswith("good-1/run.mp4"))
        self.assertEqual(d.calls.count("rec start"), 1)
        self.assertIn("Video of good run 1", render(rec))
        rec = TaskDir().prove(RecordingDevice(), by_build(proof=fails_at(4)), video=False)
        self.assertNotIn("video", rec["good"])

    def test_good_runs_spread_over_extra_devices_and_snapshot_loads_everywhere(self):
        main, other = RecordingDevice("emulator-5554"), RecordingDevice("emulator-5556")
        t = TaskDir()
        rec = prove(load_task(t.path), main, FakeMaestro(main, by_build(proof=fails_at(4))), t.dir / "out",
                    extra=[(other, FakeMaestro(other, by_build()))], snapshot="clean")
        self.assertEqual(rec["verdict"], "proven")
        self.assertEqual([r["run"] for r in rec["good"]["runs"]], list(range(1, 11)))
        by_dev = {s: [r["run"] for r in rec["good"]["runs"] if r["device"] == s] for s in ("emulator-5554", "emulator-5556")}
        self.assertEqual(by_dev["emulator-5556"], [3, 5, 7, 9])  # runs 2..10 alternate; run 1 and bugs on main
        self.assertEqual(main.snapshots, ["clean"]); self.assertEqual(other.snapshots, ["clean"])
        self.assertIn("plus 1 more for good runs", render(rec))
        self.assertEqual(other.calls[-1], "restore_clock")

    def test_environment_failure_on_an_extra_device_blocks(self):
        main, other = RecordingDevice("a"), RecordingDevice("b")
        t = TaskDir()
        bad = lambda b, f, n: FlowResult(False, error="driver did not start", environment=True)
        rec = prove(load_task(t.path), main, FakeMaestro(main, by_build(proof=fails_at(4))), t.dir / "out",
                    extra=[(other, FakeMaestro(other, bad))])
        self.assertEqual(rec["verdict"], "blocked_environment")

    def test_author_tokens_come_from_the_session_transcript(self):
        from proofloop import cost
        with tempfile.TemporaryDirectory() as root:
            tr = Path(root) / "proj" / "sess" / "subagents"
            tr.mkdir(parents=True)
            u = lambda i, o: {"input_tokens": i, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 100,
                              "output_tokens": o}
            lines = [{"requestId": "r1", "message": {"model": "claude-haiku-5-5", "usage": u(10, 5)}},
                     {"requestId": "r1", "message": {"model": "claude-haiku-5-5", "usage": u(10, 50)}},  # streamed repeat
                     {"requestId": "r2", "message": {"usage": u(20, 30)}}, {"type": "user"}]
            (tr / "agent-abc.jsonl").write_text("\n".join(json.dumps(x) for x in lines))
            usage = cost.session_usage("abc", Path(root))
            self.assertEqual((usage["output"], usage["requests"], usage["total"]), (80, 2, 310))
            self.assertEqual(usage["models"], ["claude-haiku-5-5"])
            old = cost.ROOT
            try:
                cost.session_usage.__defaults__ = (Path(root),)
                rec = TaskDir(author={"agent": "claude-code", "model": "haiku", "session": "abc"}).prove(
                    FakeDevice(), by_build(proof=fails_at(4)))
            finally:
                cost.session_usage.__defaults__ = (old,)
            self.assertEqual(rec["author_usage"]["total"], 310)
            self.assertIn("haiku; 0.3k tokens", render(rec))
            text = table([rec])
            self.assertIn("author tokens (0k per proven test)", text)
            self.assertIn("| haiku |", text)

    def test_publish_refuses_when_review_queue_is_full(self):
        import proofloop.report as rp
        t = TaskDir()
        p = t.dir / "record.json"
        p.write_text(json.dumps(t.prove(FakeDevice(), by_build(proof=fails_at(4)))))
        old = rp.open_proofloop_prs
        rp.open_proofloop_prs = lambda repo: 3
        try:
            with tempfile.TemporaryDirectory() as repo:
                subprocess.run(["git", "init", "-q", repo], check=True)
                with self.assertRaisesRegex(ValueError, "3 proofloop PRs are already open"):
                    publish(p, Path(repo), push=True)
        finally:
            rp.open_proofloop_prs = old


class Artifacts(unittest.TestCase):
    def test_record_hashes_every_input(self):
        t = TaskDir()
        rec = t.prove(FakeDevice(), by_build(proof=fails_at(4)))
        arts = rec["artifacts"]
        for name in ("task.json", "plan.md", "flow.yaml", "good.apk", "bug-proof.apk", "bug-held.apk"):
            self.assertEqual(arts[str((t.dir / name).resolve())], file_sha256(t.dir / name))
        self.assertIn("Proven against", render(rec))


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


class VacuousAndFix(unittest.TestCase):
    HEAD = 'appId: com.example.app\n---\n- launchApp:\n    stopApp: false\n- tapOn: "Garden"\n'

    def check(self, text, anchors=frozenset()):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.yaml"
            p.write_text(text)
            return check_flow(parse_flow(p), "com.example.app", anchors)

    def test_checkpoint_repeating_an_anchor_wait_is_vacuous(self):
        flow = (self.HEAD + '- extendedWaitUntil:\n    visible: "My garden"\n    timeout: 5000\n'
                '# checkpoint: C1 garden shown\n- assertVisible: "My garden"\n')
        r = self.check(flow, frozenset({"My garden"}))
        self.assertFalse(r.ok)
        self.assertIn("checkpoint C1 only repeats", r.errors[0])

    def test_two_checkpoints_on_the_same_text_with_no_action(self):
        flow = self.HEAD + '# checkpoint: C1 a\n- assertVisible: "Avocado"\n# checkpoint: C2 b\n- assertVisible: "Avocado"\n'
        self.assertIn("checkpoint C2 only repeats", " ".join(self.check(flow).errors))

    def test_new_text_or_an_action_in_between_is_fine(self):
        ok1 = self.HEAD + '# checkpoint: C1 a\n- assertVisible: "Avocado"\n- tapOn: "Avocado"\n# checkpoint: C2 b\n- assertVisible: "Avocado"\n'
        ok2 = self.HEAD + '# checkpoint: C1 a\n- assertVisible: "Avocado"\n# checkpoint: C2 b\n- assertVisible: "Avocado"\n- assertVisible: "Planted"\n'
        self.assertTrue(self.check(ok1).ok, self.check(ok1).errors)
        self.assertTrue(self.check(ok2).ok, self.check(ok2).errors)
        self.assertTrue(self.check(FLOW).ok)

    def test_fix_moves_the_marker_and_repairs_launchapp(self):
        round1 = ('appId: com.example.app\n---\n- launchApp\n- tapOn: "Garden"\n'
                  '- extendedWaitUntil:\n    visible: "Avocado"\n    timeout: 5000\n'
                  '# checkpoint: C1 plant listed\n- assertVisible: "Avocado"\n')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.yaml"
            p.write_text(round1)
            self.assertFalse(check_flow(parse_flow(p), "com.example.app").ok)
            fixes = fix_flow(p)
            self.assertEqual(len(fixes), 2, fixes)
            r = check_flow(parse_flow(p), "com.example.app")
            self.assertTrue(r.ok, r.errors)
            text = p.read_text()
            self.assertLess(text.index("# checkpoint: C1"), text.index("extendedWaitUntil"))
            self.assertIn("stopApp: false", text)
            self.assertEqual(fix_flow(p), [])  # idempotent

    def test_fix_leaves_anchor_waits_and_clean_flows_alone(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.yaml"
            p.write_text(FLOW)
            self.assertEqual(fix_flow(p), [])
            self.assertEqual(p.read_text(), FLOW)
            gated = (self.HEAD + '- extendedWaitUntil:\n    visible: "My garden"\n    timeout: 5000\n'
                     '# checkpoint: C1 plant\n- assertVisible: "Avocado"\n')
            p.write_text(gated)
            self.assertEqual(fix_flow(p, frozenset({"My garden"})), [])

    def test_fix_drops_clear_state_and_flips_stop_app(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.yaml"
            p.write_text('appId: com.example.app\n---\n- launchApp:\n    clearState: true\n    stopApp: true\n'
                         '# checkpoint: C1 a\n- assertVisible: "X"\n')
            fixes = fix_flow(p)
            self.assertEqual(sorted(fixes), sorted(["removed launchApp clearState: true (the runner resets app data)",
                                                    "changed launchApp stopApp: true to false"]))
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

    def test_flow_edited_after_proof_is_not_published(self):
        t = TaskDir()
        rec = t.prove(FakeDevice(), by_build(proof=fails_at(4)))
        p = t.dir / "record.json"
        p.write_text(json.dumps(rec))
        (t.dir / "flow.yaml").write_text(FLOW.replace('"Item"', '"Item.*"'))
        with self.assertRaisesRegex(ValueError, "changed since it was proven"):
            publish(p, t.dir)

    def test_record_without_hashes_is_not_published(self):
        t = TaskDir()
        rec = t.prove(FakeDevice(), by_build(proof=fails_at(4)))
        del rec["artifacts"]
        p = t.dir / "record.json"
        p.write_text(json.dumps(rec))
        with self.assertRaisesRegex(ValueError, "no artifact hashes"):
            publish(p, t.dir)

    def test_results_table(self):
        rec = TaskDir().prove(FakeDevice(), by_build(proof=fails_at(4), held=fails_at(5)))
        text = table([rec], "full loop")
        self.assertIn("proof rate 1/1", text)
        self.assertIn("held-out bug-catch rate 1/1", text)


if __name__ == "__main__":
    unittest.main()
