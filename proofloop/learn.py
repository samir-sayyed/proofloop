"""Self-learning app memory: learn facts about the good build from runs, never from bug builds.

The hand-written app map (app-map.md) stays human-owned. This module keeps a ledger next to it,
app-memory.json, and renders the facts it is sure of into learned.md, which the authoring skill
reads after the map. Write path:

  observe   parse Maestro command logs from good-build runs only:
            - authoring attempts (`proofloop try`, or imported ~/.maestro/tests sessions)
            - the good runs of proof records (the bug runs are never read)
  extract   edge     a tap between two screens recognised by the map's human anchors
            locator  a visibility check that failed on exact text X and later passed with X'
                     where X' matches X (e.g. "Next start: ...AM" -> "Next start: ...AM.*")
            slow     a wait that used at least half of its timeout
            flaky    a step that failed on some good runs of a proof and passed on others
  gate      every fact keeps its evidence (source id, build). A fact is confirmed only when it
            is re-observed (edges, slow waits: 2+ runs; locator: the fixed form passed 2+ times);
            a locator fact is contradicted when the exact text later passes on the same screen;
            a fact not seen on the newest build whose screen was seen there is stale.
  render    learned.md lists confirmed facts, then candidates and stale ones. It never writes
            anchors: only human anchors may exempt a wait from the checkpoint rule.

Sources are ingested once (by id) and the ledger accumulates, so `learn` can run after every
attempt or proof.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .appmap import load as load_map

IMPLICIT = {"defineVariablesCommand", "applyConfigurationCommand"}


@dataclass
class Step:
    kind: str        # tap | visible | notvisible | input | back | launch | other
    text: str
    passed: bool
    duration: int    # ms
    timeout: int     # ms, 0 if none


def parse_commands(path) -> list[Step]:
    steps = []
    for c in json.loads(Path(path).read_text()):
        name, body = next(iter(c["command"].items()))
        if name in IMPLICIT:
            continue
        meta = c.get("metadata", {})
        kind, text, timeout = "other", "", int(body.get("timeout", 0) or 0) if isinstance(body, dict) else 0
        if name == "tapOnElement":
            kind, text = "tap", body.get("selector", {}).get("textRegex", "")
        elif name == "assertConditionCommand":
            cond = body.get("condition", {})
            if "visible" in cond:
                kind, text = "visible", cond["visible"].get("textRegex", "")
            elif "notVisible" in cond:
                kind, text = "notvisible", cond["notVisible"].get("textRegex", "")
        elif name == "inputTextCommand":
            kind, text = "input", body.get("text", "")
        elif name == "backPressCommand":
            kind = "back"
        elif name == "launchAppCommand":
            kind = "launch"
        steps.append(Step(kind, text or "", meta.get("status") == "COMPLETED", int(meta.get("duration") or 0), timeout))
    return steps


def _stamp(when: str) -> str:
    """Comparable time from any of '2026-11-21T11:02:32', '20261121-110232', '2026-11-21_115557'."""
    return re.sub(r"\D", "", when or "")[:14]


def _matches(pattern: str, text: str) -> bool:
    try:
        return re.fullmatch(pattern, text, re.S) is not None
    except re.error:
        return False


class Memory:
    def __init__(self, app_dir):
        self.dir = Path(app_dir)
        self.path = self.dir / "app-memory.json"
        m = load_map(self.dir / "app-map.md")
        self.app = m.app
        owners: dict[str, list[str]] = {}
        for s in m.screens.values():
            for a in s.anchors:
                owners.setdefault(a, []).append(s.id)
        self.anchor_screen = {a: ids[0] for a, ids in owners.items() if len(ids) == 1}  # ambiguous anchors skipped
        data = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.sources: list[dict] = data.get("sources", [])
        self.facts: dict[str, dict] = data.get("facts", {})
        self.seen_screens: dict[str, list[str]] = data.get("seen_screens", {})  # build -> screens observed
        self.pending: dict[str, str] = data.get("pending", {})
        self.current_build: str | None = data.get("current_build")  # set with `learn --current-build`  # exact text that failed -> screen, awaiting a fix

    # -- write path ---------------------------------------------------------------------------
    def ingest_session(self, source_id: str, build: str, runs: list[list[Step]], when: str = "") -> bool:
        """One attempt, or the good runs of one proof, all on the good build `build`, run at time `when`."""
        if any(s["id"] == source_id for s in self.sources):
            return False
        if not build or "bug" in build.lower():
            raise ValueError(f"refusing to learn from build {build!r}: memory learns from the good build only")
        self.sources.append({"id": source_id, "build": build, "runs": len(runs), "when": _stamp(when)})
        failed_exact = self.pending  # persists across attempts: a failure now, the fix in a later attempt
        for steps in runs:
            screen, taps = None, []
            for i, st in enumerate(steps):
                if st.kind == "visible" and st.passed and st.text in self.anchor_screen:
                    new = self.anchor_screen[st.text]
                    self._saw(build, new)
                    if screen and new != screen and len(taps) == 1:  # one tap: that tap made the transition
                        self._fact(f"edge|{screen}|{taps[0]}|{new}", "edge", screen, source_id, build,
                                   {"tap": taps[0], "to": new})
                    elif screen and new != screen and taps:  # several taps: a route, screens between unknown
                        self._fact(f"route|{screen}|{'>'.join(taps)}|{new}", "route", screen, source_id, build,
                                   {"taps": taps, "to": new})
                    if new != screen:
                        screen, taps = new, []
                    continue
                if st.kind == "tap" and st.passed:
                    taps.append(st.text)
                if st.kind == "visible" and not st.passed and screen:
                    failed_exact[st.text] = screen
                if st.kind == "visible" and st.passed:
                    for exact, scr in list(failed_exact.items()):
                        if exact != st.text and _matches(st.text, exact):
                            self._fact(f"locator|{scr}|{exact}", "locator", scr, source_id, build,
                                       {"failed": exact, "works": st.text})
                            del failed_exact[exact]
                    for key, f in self.facts.items():
                        if f["kind"] == "locator" and f["data"]["failed"] == st.text and f["screen"] == screen:
                            f["status_note"] = "contradicted: the exact text passed later"
                    for key, f in self.facts.items():
                        if f["kind"] == "locator" and f["data"]["works"] == st.text:
                            f["passes"] = f.get("passes", 0) + 1
                            if build not in f["builds"]:
                                f["builds"].append(build)  # re-observed on this build
                if st.kind == "visible" and st.passed and st.timeout and st.duration >= st.timeout / 2 and screen:
                    self._fact(f"slow|{screen}|{st.text}", "slow", screen, source_id, build,
                               {"text": st.text, "timeout_ms": st.timeout}, max_ms=st.duration)
                if not st.passed:
                    break  # Maestro stops at the first failure
        return True

    def ingest_flaky(self, source_id: str, build: str, runs: list[list[Step]]) -> None:
        """Good runs of one proof: a step that failed on some runs and passed on others is a hazard."""
        if len(runs) < 2:
            return
        by_pos: dict[tuple, list[bool]] = {}
        for steps in runs:
            for i, st in enumerate(steps):
                by_pos.setdefault((i, st.kind, st.text), []).append(st.passed)
                if not st.passed:
                    break
        for (i, kind, text), res in by_pos.items():
            if not all(res) and any(res):
                self._fact(f"flaky|{kind}|{text}", "flaky", "", source_id, build,
                           {"step": f"{kind} \"{text}\"", "failed": res.count(False), "runs": len(res)})

    def _saw(self, build, screen):
        lst = self.seen_screens.setdefault(build, [])
        if screen not in lst:
            lst.append(screen)

    def _fact(self, key, kind, screen, source_id, build, data, max_ms=None):
        f = self.facts.setdefault(key, {"kind": kind, "screen": screen, "data": data, "sources": [],
                                        "builds": [], "runs": 0})
        f["runs"] += 1
        if source_id not in f["sources"]:
            f["sources"].append(source_id)
        if build not in f["builds"]:
            f["builds"].append(build)
        if max_ms is not None:
            f["data"]["max_ms"] = max(f["data"].get("max_ms", 0), max_ms)

    # -- manage -------------------------------------------------------------------------------
    def newest_build(self) -> str | None:
        """The current build if set, else the build of the most recent run (by run time, not ingest order)."""
        if self.current_build:
            return self.current_build
        if not self.sources:
            return None
        return max(enumerate(self.sources), key=lambda p: (p[1].get("when", ""), p[0]))[1]["build"]

    def status(self, f) -> str:
        if f.get("status_note", "").startswith("contradicted"):
            return "contradicted"
        newest = self.newest_build()
        if (f["kind"] != "route" and newest and newest not in f["builds"]  # a route is one example path, not a claim
                and f["screen"] in self.seen_screens.get(newest, [])):
            return "stale"
        if f["kind"] == "locator":
            return "confirmed" if f.get("passes", 0) >= 2 else "candidate"
        return "confirmed" if f["runs"] >= 2 else "candidate"

    def save(self):
        self.path.write_text(json.dumps({"app": self.app, "sources": self.sources, "facts": self.facts,
                                         "seen_screens": self.seen_screens,
                                         "pending": self.pending,
                                         "current_build": self.current_build}, indent=1) + "\n")

    # -- read path ----------------------------------------------------------------------------
    def render(self) -> str:
        groups = {"confirmed": [], "candidate": [], "stale": [], "contradicted": []}
        for f in sorted(self.facts.values(), key=lambda f: (f["screen"], f["kind"], json.dumps(f["data"]))):
            groups[self.status(f)].append(f)
        out = [f"# Learned memory: {self.app}", "",
               "> Generated by `proofloop learn` from good-build runs only. Do not edit; promote a fact into",
               "> app-map.md by hand if it should become a rule. Learned facts never add anchors.",
               f"> Sources: {len(self.sources)} ({sum(s['runs'] for s in self.sources)} runs). "
               f"Newest build: {self.newest_build()}.", ""]
        titles = {"confirmed": "Confirmed (re-observed)", "candidate": "Candidates (seen once; verify)",
                  "stale": "Stale (not seen on the newest build; recheck)", "contradicted": "Contradicted"}
        for g in ("confirmed", "candidate", "stale", "contradicted"):
            if groups[g]:
                out += [f"## {titles[g]}", ""] + [f"- {self._line(f)}" for f in groups[g]] + [""]
        return "\n".join(out)

    def _line(self, f) -> str:
        d, s = f["data"], f["screen"]
        ev = f"({f['runs']} runs, {len(f['sources'])} sources, builds {', '.join(f['builds'])})"
        if f["kind"] == "edge":
            return f'{s}: tap "{d["tap"]}" -> {d["to"]} {ev}'
        if f["kind"] == "locator":
            return (f'{s}: "{d["failed"]}" is not found as exact text; "{d["works"]}" works '
                    f'(the element text continues past it) (failed then fixed in {f["runs"]} sessions; '
                    f'fixed form passed {f.get("passes", 0)} times; builds {", ".join(f["builds"])})')
        if f["kind"] == "route":
            return f'{s} -> {d["to"]}: tap {", then ".join(chr(34) + t + chr(34) for t in d["taps"])} {ev}'
        if f["kind"] == "slow":
            return f'{s}: waiting for "{d["text"]}" took up to {d["max_ms"]} ms of a {d["timeout_ms"]} ms timeout {ev}'
        if f["kind"] == "flaky":
            return f'{d["step"]} failed on {d["failed"]} of {d["runs"]} good runs of one proof {ev}'
        return json.dumps(f)


def runs_from_record_dir(record_dir) -> tuple[str, str, list[list[Step]], str]:
    """(source id, build, good runs, start time) from a proof output dir. Bug runs are never read."""
    record_dir = Path(record_dir)
    for f in (record_dir / "record.json", record_dir.with_name(record_dir.name + ".record.json")):  # prove / eval layout
        if f.exists():
            rec = json.loads(f.read_text())
            break
    else:
        raise FileNotFoundError(f"no record.json for {record_dir}")
    build = Path(rec["good"]["apk"]).stem
    runs = []
    for run_dir in sorted(record_dir.glob("good-*"), key=lambda p: int(p.name.split("-")[1])):
        cmds = sorted(run_dir.glob("**/commands.json"))
        steps = [st for c in cmds for st in parse_commands(c)]
        if steps:
            runs.append(steps)
    return f"proof:{rec['task']}@{rec.get('started', record_dir.name)}", build, runs, rec.get("started", "")


def runs_from_attempts(attempt_dirs) -> list[list[Step]]:
    """One run per attempt dir, in time order; a multi-flow task's flows are joined in step order,
    the same way proof runs are."""
    runs = []
    for d in sorted(Path(a) for a in attempt_dirs):
        steps = [st for c in sorted(d.glob("**/commands.json")) for st in parse_commands(c)]
        if steps:
            runs.append(steps)
    return runs


def is_bug_or_scoring_run(maestro_log: str) -> bool:
    """Imported Maestro sessions: skip anything that ran a bug build or came from a scoring/proof folder."""
    return bool(re.search(r"/score/|/proofloop-out/|/eval-out/|\bbug-[\w.-]*\.apk", maestro_log))
