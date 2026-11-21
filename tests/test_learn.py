import json
import tempfile
import unittest
from pathlib import Path

from proofloop.learn import Memory, is_bug_or_scoring_run, parse_commands, runs_from_attempts, runs_from_record_dir

MAP = '''# App map: Demo
app: com.example.demo

## screen: home
anchors: "Home title"
- tap "Add" -> editor

## screen: editor
anchors: "Editor title"
- tap "Save" -> saved

## screen: saved
anchors: "Saved title"
'''


def cmd(kind, text="", ok=True, ms=100, timeout=None):
    if kind == "tap":
        c = {"tapOnElement": {"selector": {"textRegex": text}}}
    elif kind == "visible":
        c = {"assertConditionCommand": {"condition": {"visible": {"textRegex": text}}}}
        if timeout:
            c["assertConditionCommand"]["timeout"] = str(timeout)
    else:
        c = {"inputTextCommand": {"text": text}}
    return {"command": c, "metadata": {"status": "COMPLETED" if ok else "FAILED", "duration": ms}}


def write_run(d: Path, cmds):
    d.mkdir(parents=True, exist_ok=True)
    (d / "commands.json").write_text(json.dumps(cmds))


class LearnTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = Path(self.tmp.name)
        (self.app / "app-map.md").write_text(MAP)

    def tearDown(self):
        self.tmp.cleanup()

    def attempt(self, name, cmds):
        d = self.app / "attempts" / name / "flow"
        write_run(d, cmds)
        return runs_from_attempts([d.parent])

    def test_edges_routes_and_locator_fix_across_attempts(self):
        mem = Memory(self.app)
        fail = [cmd("visible", "Home title"), cmd("tap", "Add"), cmd("visible", "Editor title"),
                cmd("tap", "Name"), cmd("input", "x"), cmd("tap", "Save"), cmd("visible", "Saved title"),
                cmd("visible", "Next start: 9:00 AM", ok=False)]
        ok = fail[:-1] + [cmd("visible", "Next start: 9:00 AM.*")]
        mem.ingest_session("a1", "good-1", self.attempt("1", fail))
        mem.ingest_session("a2", "good-1", self.attempt("2", ok))
        f = mem.facts["locator|saved|Next start: 9:00 AM"]
        self.assertEqual(mem.status(f), "candidate")  # fixed form passed once
        mem.ingest_session("a3", "good-1", self.attempt("3", ok))
        self.assertEqual(mem.status(f), "confirmed")
        self.assertIn("edge|home|Add|editor", mem.facts)                      # one tap: an edge
        self.assertIn("route|editor|Name>Save|saved", mem.facts)              # several taps: a route
        self.assertNotIn("edge|editor|Save|saved", mem.facts)
        self.assertEqual(mem.status(mem.facts["edge|home|Add|editor"]), "confirmed")

    def test_exact_text_passing_later_contradicts_the_locator_fact(self):
        mem = Memory(self.app)
        base = [cmd("visible", "Saved title")]
        mem.ingest_session("a1", "good-1", self.attempt("1", base + [cmd("visible", "Done", ok=False)]))
        mem.ingest_session("a2", "good-1", self.attempt("2", base + [cmd("visible", "Done.*")]))
        mem.ingest_session("a3", "good-1", self.attempt("3", base + [cmd("visible", "Done")]))
        self.assertEqual(mem.status(mem.facts["locator|saved|Done"]), "contradicted")

    def test_stale_on_a_newer_build_but_routes_are_not(self):
        mem = Memory(self.app)
        run = [cmd("visible", "Home title"), cmd("tap", "Add"), cmd("visible", "Editor title"),
               cmd("tap", "A"), cmd("tap", "B"), cmd("visible", "Saved title")]
        mem.ingest_session("old", "good-1", self.attempt("1", run))
        mem.ingest_session("old2", "good-1", self.attempt("2", run))
        mem.ingest_session("new", "good-2", self.attempt("3", [cmd("visible", "Home title"), cmd("visible", "Editor title")]))
        self.assertEqual(mem.status(mem.facts["edge|home|Add|editor"]), "stale")
        self.assertNotEqual(mem.status(mem.facts["route|editor|A>B|saved"]), "stale")

    def test_never_learns_from_bug_builds(self):
        out = self.app / "proof"
        bug = [cmd("visible", "Home title"), cmd("tap", "Add"), cmd("visible", "Editor title"),
               cmd("visible", "Weekdays", ok=False)]
        good = [cmd("visible", "Home title"), cmd("tap", "Add"), cmd("visible", "Editor title"), cmd("visible", "Weekdays")]
        write_run(out / "good-1" / "step1-flow" / "t" / "flow", good)
        write_run(out / "weekdays-off-by-one-1" / "step1-flow" / "t" / "flow", bug)
        (out / "record.json").write_text(json.dumps({"task": "demo/t", "started": "x", "good": {"apk": "a/good-1.apk"}}))
        sid, build, runs, _ = runs_from_record_dir(out)
        self.assertEqual((build, len(runs)), ("good-1", 1))
        mem = Memory(self.app)
        mem.ingest_session(sid, build, runs)
        self.assertFalse([k for k in mem.facts if "Weekdays" in k])
        self.assertFalse(mem.pending)  # the bug run's failure never became a pending locator fact
        with self.assertRaises(ValueError):
            mem.ingest_session("b", "bug-weekdays-off-by-one-1", runs)

    def test_learning_never_touches_the_map_or_its_anchors(self):
        mem = Memory(self.app)
        mem.ingest_session("a1", "good-1", self.attempt("1", [cmd("visible", "Home title"), cmd("tap", "Add"),
                                                             cmd("visible", "Editor title")]))
        mem.save()
        (self.app / "learned.md").write_text(mem.render())
        self.assertEqual((self.app / "app-map.md").read_text(), MAP)
        self.assertNotIn("anchors:", (self.app / "learned.md").read_text())

    def test_staleness_follows_run_time_not_ingest_order(self):
        mem = Memory(self.app)
        new = [cmd("visible", "Home title"), cmd("tap", "Add"), cmd("visible", "Editor title")]
        old = [cmd("visible", "Home title"), cmd("tap", "New"), cmd("visible", "Editor title")]
        mem.ingest_session("new", "good-2", self.attempt("2", new), "2026-11-21_120000")
        mem.ingest_session("old", "good-1", self.attempt("1", old), "2026-11-17_090000")  # ingested later, ran earlier
        self.assertEqual(mem.newest_build(), "good-2")
        self.assertEqual(mem.status(mem.facts["edge|home|New|editor"]), "stale")
        self.assertNotEqual(mem.status(mem.facts["edge|home|Add|editor"]), "stale")

    def test_slow_wait_and_flaky_step(self):
        mem = Memory(self.app)
        slow = [cmd("visible", "Home title"), cmd("visible", "Loaded", ms=7000, timeout=10000)]
        mem.ingest_session("a1", "good-1", self.attempt("1", slow))
        mem.ingest_session("a2", "good-1", self.attempt("2", slow))
        f = mem.facts["slow|home|Loaded"]
        self.assertEqual((f["data"]["max_ms"], mem.status(f)), (7000, "confirmed"))
        ok = [cmd("visible", "Home title"), cmd("tap", "Add")]
        bad = [cmd("visible", "Home title"), cmd("tap", "Add", ok=False)]
        runs = [self.attempt(n, c)[0] for n, c in (("p1", ok), ("p2", bad), ("p3", ok))]
        mem.ingest_flaky("proof", "good-1", runs)
        self.assertEqual(mem.facts['flaky|tap|Add']["data"]["failed"], 1)

    def test_multi_flow_attempt_is_one_run(self):
        d = self.app / "attempts" / "x"
        write_run(d / "good-1" / "step1-setup" / "t" / "flow", [cmd("visible", "Home title"), cmd("tap", "Add")])
        write_run(d / "good-1" / "step2-check" / "t" / "flow", [cmd("visible", "Editor title")])
        runs = runs_from_attempts([d])
        self.assertEqual(len(runs), 1)
        mem = Memory(self.app)
        mem.ingest_session("x", "good-1", runs)
        self.assertIn("edge|home|Add|editor", mem.facts)  # the screen carried across the two flows

    def test_import_skips_scoring_and_bug_runs(self):
        self.assertTrue(is_bug_or_scoring_run("Flow /tmp/exp/l1/score/flow.yaml"))
        self.assertTrue(is_bug_or_scoring_run("installing bug-next-skips-today-e4ba3eb.apk"))
        self.assertFalse(is_bug_or_scoring_run("Flow /tmp/exp/l1/flow.yaml debug output"))

    def test_parse_skips_implicit_commands(self):
        p = self.app / "c.json"
        p.write_text(json.dumps([{"command": {"defineVariablesCommand": {}}, "metadata": {"status": "COMPLETED"}},
                                 cmd("tap", "Add")]))
        self.assertEqual([s.kind for s in parse_commands(p)], ["tap"])


if __name__ == "__main__":
    unittest.main()
