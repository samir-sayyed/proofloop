"""History, mined bugs, retro, backfill queue and fix scaffolding."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from proofloop import history
from proofloop.mine import fix_commits
from proofloop.retro import cause, retro


def rec(verdict, started, good="sha256:" + "a" * 64, runs=10, bugs=(), label=None, reason=""):
    return {"verdict": verdict, "started": started, "failure_label": label, "reason": reason, "task": "x/y",
            "flows": ["/t/flow.yaml"], "artifacts": {"/t/flow.yaml": "sha256:" + "f" * 64, "/t/good.apk": good},
            "good": {"runs": [{"passed": True, "step": "", "run": i} for i in range(runs)], "required": 10},
            "bugs": list(bugs)}


class FakeTask:
    def __init__(self, d):
        self.dir, self.good = Path(d), Path("/t/good.apk")


class History(unittest.TestCase):
    def test_shelf_life_across_builds_and_first_break(self):
        with tempfile.TemporaryDirectory() as d:
            t = FakeTask(d)
            history.append(t, rec("proven", "2026-11-14T10:00:00"), "r1")
            history.append(t, rec("proven", "2026-11-20T10:00:00", good="sha256:" + "b" * 64), "r2")
            history.append(t, rec("blocked_environment", "2026-11-21T10:00:00"), "r3")  # not a break
            self.assertIn("proven on 2 good build(s)", history.summary(history.load(d)))
            self.assertIn("shelf life so far 7 days", history.summary(history.load(d)))
            history.append(t, rec("rejected_missed_bug", "2026-11-23T10:00:00", good="sha256:" + "c" * 64), "r4")
            s = history.summary(history.load(d))
            self.assertIn("stopped being proven on 2026-11-23 (build cccccccccccc: rejected_missed_bug) after 9 days", s)

    def test_empty_and_never_proven(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(history.summary(history.load(d)), "no proofs recorded yet")
            history.append(FakeTask(d), rec("rejected_flaky", "2026-11-14T10:00:00"), "r")
            self.assertEqual(history.summary(history.load(d)), "1 proofs, never proven")


class MineBugs(unittest.TestCase):
    def test_source_fixes_ranked_by_topic_and_size(self):
        with tempfile.TemporaryDirectory() as repo:
            g = lambda *a: subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True, text=True)
            g("init", "-q"); g("config", "user.email", "t@e.com"); g("config", "user.name", "t")
            def commit(msg, **files):
                for name, text in files.items():
                    p = Path(repo) / name.replace("__", "/")
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(text)
                g("add", "-A"); g("commit", "-q", "-m", msg)
            commit("init", **{"app__Home.kt": "a"})
            commit("Fix weekday summary on Home", **{"app__ui__HomeScreen.kt": "b"})
            commit("fix typo in README", **{"README.md": "x"})                       # docs only: skipped
            commit("Fix flaky test", **{"app__test__HomeTest.kt": "t"})               # test only: skipped
            commit("Add prefix option", **{"app__Prefix.kt": "p"})                    # "prefix" is not "fix"
            commit("fix: crash in billing", **{"app__Billing.kt": "c"})
            rows = fix_commits(repo, "A Weekdays schedule shows on Home with its summary")
            self.assertEqual([r["subject"] for r in rows], ["Fix weekday summary on Home", "fix: crash in billing"])
            self.assertEqual(rows[0]["overlap"], ["home", "summary"])


class Retro(unittest.TestCase):
    def bug(self, passed, checkpoint):
        return {"role": "proof", "caught": False, "name": "b",
                "result": {"passed": passed, "checkpoint": checkpoint, "step": "flow.yaml:7 extendedWaitUntil"}}

    def test_causes(self):
        self.assertEqual(cause(rec("rejected_missed_bug", "t", bugs=[self.bug(False, "setup")])), "hidden_by_setup")
        self.assertEqual(cause(rec("rejected_missed_bug", "t", bugs=[self.bug(True, None)])), "not_observed")
        self.assertEqual(cause(rec("rejected_missed_bug", "t", bugs=[self.bug(False, "C1")])), "wrong_checkpoint")
        self.assertEqual(cause(rec("rejected_flaky", "t", label="bad_locator")), "locator")
        broke = rec("rejected_flaky", "t", runs=3, label="flaky")
        for x in broke["good"]["runs"]:
            x.update(passed=False, checkpoint="setup", step="flow.yaml:13 extendedWaitUntil")
        self.assertEqual(cause(broke), "broken_setup")
        broke["good"]["runs"][0]["passed"] = True
        self.assertEqual(cause(broke), "flaky")
        self.assertEqual(cause(rec("needs_human", "t", reason="plan.md changed since it was approved")), "approval")

    def test_recurring_causes_are_grouped_with_their_fix(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(2):
                p = Path(d) / f"t{i}" / "record.json"
                p.parent.mkdir()
                p.write_text(json.dumps(rec("rejected_missed_bug", "t", bugs=[self.bug(False, "setup")])))
            (Path(d) / "ok.record.json").write_text(json.dumps(rec("proven", "t")))
            text = retro([d, d])  # overlapping paths are not double counted
            self.assertIn("3 records: 1 proven, 2 not proven", text)
            self.assertIn("2x hidden_by_setup (RECURRING)", text)
            self.assertIn("proofloop check --fix", text)


MAP = '''# App map: Demo
app: com.example.demo

## screen: home
anchors: "Home"
- tap "Add" -> editor
- tap "Help" -> help
- rule: an empty list reads "Nothing yet"
- rule: lists items with their "Saved" date
- rule: a text locator for multi-line text needs a trailing .*

## screen: editor
anchors: "New item"

## screen: help
anchors: "Help center"
'''


class Backlog(unittest.TestCase):
    def test_rules_screens_and_actions_no_flow_covers(self):
        from proofloop.factory import backlog
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "app-map.md").write_text(MAP)
            (Path(d) / "t1").mkdir()
            (Path(d) / "t1" / "flow.yaml").write_text('- tapOn: "Add"\n- assertVisible: "New item"\n- assertVisible: "Saved"\n')
            items = backlog(d)
            kinds = [(i["kind"], i["screen"]) for i in items]
            self.assertEqual(kinds[0], ("rule", "home"))
            self.assertIn("Nothing yet", items[0]["criterion"])
            self.assertNotIn("Saved", " ".join(i["criterion"] for i in items))  # covered rule
            self.assertNotIn("locator", " ".join(i["criterion"] for i in items))  # author guidance, not behaviour
            self.assertIn(("screen", "help"), kinds)
            self.assertIn(("action", "home"), kinds)  # tap "Help"
            self.assertNotIn(("screen", "editor"), kinds)


class FromFix(unittest.TestCase):
    def test_scaffold_uses_the_fix_as_good_and_its_parent_as_proof_bug(self):
        from proofloop.factory import from_fix
        with tempfile.TemporaryDirectory() as root:
            repo, app = Path(root) / "repo", Path(root) / "tasks" / "demo"
            repo.mkdir(); app.mkdir(parents=True)
            g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout
            g("init", "-q"); g("config", "user.email", "t@e.com"); g("config", "user.name", "t")
            (repo / "A.kt").write_text("a"); g("add", "-A"); g("commit", "-q", "-m", "init")
            (repo / "A.kt").write_text("b"); g("add", "-A"); g("commit", "-q", "-m", "fix: weekday summary\n\nIt said Weekend.")
            fix, parent = g("rev-parse", "HEAD").strip(), g("rev-parse", "HEAD^").strip()
            (app / "other").mkdir()
            (app / "other" / "task.json").write_text(json.dumps({"app_id": "com.example.demo", "device": {"timezone": "UTC"}}))
            d = from_fix(repo, "HEAD", app, "weekday-fix")
            t = json.loads((d / "task.json").read_text())
            self.assertEqual(t["criterion"], f"Regression test for {fix[:7]}: weekday summary")
            self.assertTrue(t["good"].endswith(f"good-{fix[:7]}.apk"))
            self.assertTrue(t["bugs"][0]["apk"].endswith(f"good-{parent[:7]}.apk"))
            self.assertEqual((t["app_id"], t["bugs"][0]["role"]), ("com.example.demo", "proof"))
            self.assertIn("It said Weekend.", (d / "plan.md").read_text())
            self.assertNotIn("approved_plan", t)  # a scaffold is never approved
            with self.assertRaises(FileExistsError):
                from_fix(repo, "HEAD", app, "weekday-fix")


if __name__ == "__main__":
    unittest.main()
