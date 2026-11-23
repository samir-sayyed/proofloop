"""proofloop command line.

  proofloop check  TASK            check flows: allowlist, checkpoints, coordinate fallbacks
  proofloop approve TASK --by NAME bind a human's approval to the current plan.md (run by the human)
  proofloop prove  TASK [--out D]  run the proof on a device and write the run record and report
  proofloop report RECORD          print the report for a run record
  proofloop publish RECORD --repo PATH [--push]   commit a proven test to the app repo (and open a PR)
  proofloop eval   DIR [--config NAME] [--runs N] prove every task under DIR and print a results table
  proofloop prepare TASK           install the good build, reset the app, pin the clock (start state for exploring)
  proofloop probe                  print the device sound state (read-only)
  proofloop doctor                 check adb, device, Maestro and free space
  proofloop map    MAP [FLOWS...]  check an app map; with flow files or dirs, report screens/actions no flow covers
  proofloop try    TASK            run the task once on the good build, keep the attempt, learn from it
  proofloop learn  APP_DIR [...]   learn app memory from proofs, attempts or imported Maestro runs
  proofloop history TASK           proof history and shelf life of the task's test
  proofloop mine-bugs REPO [--task T]  fix commits whose parent is a real held-out bug
  proofloop retro  PATHS...        group rejected proofs by cause, with the rule or step for each
  proofloop next   APP_DIR         backfill queue: what no flow covers yet, rules first
  proofloop from-fix REPO SHA --app-dir D --name N   regression-test task from a real fix

Exit codes: 0 proven / ok, 1 not proven, 2 usage or setup error.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from .device import DeviceError
from .flow import check_task_flows
from .report import load_record, publish, render
from .task import TaskError, approve, load_task


def _device(args):
    from .device import AdbDevice
    return AdbDevice(args.device)


def _maestro(device):
    from .maestro import MaestroRunner
    return MaestroRunner(device.serial)


def _extra(args) -> list:
    """--devices A,B: more devices to spread good runs over (the main device is --device)."""
    from .device import AdbDevice
    out = []
    for s in filter(None, (getattr(args, "devices", None) or "").split(",")):
        d = AdbDevice(s.strip())
        out.append((d, _maestro(d)))
    return out


def cmd_check(args) -> int:
    task = load_task(args.task)
    if args.fix:
        from .flow import fix_flow, task_anchors
        for p in task.flow_paths():
            for f in fix_flow(p, task_anchors(task)):
                print(f"FIXED {p.name}: {f}")
    result, flows = check_task_flows(task)
    for p, f in flows.items():
        cps = ", ".join(sorted(f.checkpoints)) or "none"
        print(f"{Path(p).name}: {len(f.commands)} commands, checkpoints: {cps}")
    if task.probe_checkpoints():
        print(f"probe checkpoints: {', '.join(task.probe_checkpoints())}")
    for e in result.errors:
        print(f"ERROR {e}")
    for f in result.fallbacks:
        print(f"FLAG  {f}")
    # Approval is a human step, so it is reported but never fails `check` (prove enforces it).
    declared = {cp for f in flows.values() for cp in f.checkpoints} | set(task.probe_checkpoints())
    problem = task.approval_problem(declared)
    print(f"WARN  approval: {problem}" if problem else "approval: plan.md approved and matches the flows")
    print("ok" if result.ok else "not ok")
    return 0 if result.ok else 1


def cmd_approve(args) -> int:
    print(approve(args.task, args.by, datetime.now().date().isoformat()))
    return 0


def cmd_prove(args) -> int:
    from .verify import prove
    task = load_task(args.task)
    if args.runs:
        task.good_runs = args.runs
    out = Path(args.out or task.dir / "proofloop-out" / datetime.now().strftime("%Y%m%d-%H%M%S"))
    out.mkdir(parents=True, exist_ok=True)
    device = _device(args)
    record = prove(task, device, _maestro(device), out, fail_fast=args.fail_fast, extra=_extra(args),
                   snapshot=args.snapshot, video=args.video)
    (out / "record.json").write_text(json.dumps(record, indent=2))
    (out / "report.md").write_text(render(record))
    print(render(record))
    print(f"record: {out / 'record.json'}")
    from . import history
    history.append(task, record, out / "record.json")
    print(f"history: {history.summary(history.load(task.dir))}")
    app = _app_dir(task)
    if app and args.learn:
        try:
            print(_learn_proof(app, out))
        except Exception as e:  # learning never changes a verdict
            print(f"memory not updated: {e}")
    return 0 if record["verdict"] == "proven" else 1


def cmd_history(args) -> int:
    from . import history
    task = load_task(args.task)
    rows = history.load(task.dir)
    for r in rows:
        print(f"{r['date']}  {r['verdict']:<20} good {r['good']}  flows {r['flows']}  runs {r['good_runs']}/{r['required']}")
    print(history.summary(rows))
    return 0


def cmd_mine(args) -> int:
    from .mine import fix_commits
    crit = load_task(args.task).criterion if args.task else ""
    rows = fix_commits(Path(args.repo), crit, limit=args.limit, since=args.since)
    for c in rows:
        on = f" on topic: {', '.join(c['overlap'])}" if c["overlap"] else ""
        print(f"{c['sha']}  parent {c['parent']}  {c['date']}  {c['files']} files  score {c['score']:>5}  {c['subject']}{on}")
    print(f"{len(rows)} candidates. Build the parent of a fix as a held_out bug "
          f"(e.g. tasks/quiet-hours/build-apks.sh REPO PARENT) and prove: does the test catch a real regression?")
    return 0


def cmd_next(args) -> int:
    from .factory import backlog
    items = backlog(Path(args.app_dir))
    for i in items[:args.limit]:
        print(f"[{i['kind']:<6}] {i['criterion']}")
    print(f"{len(items)} untested items in {args.app_dir} (showing {min(len(items), args.limit)}). "
          "Pick one, write plan.md, get it approved, then prove.")
    return 0


def cmd_from_fix(args) -> int:
    from .factory import from_fix
    d = from_fix(Path(args.repo), args.sha, Path(args.app_dir), args.name)
    print(f"scaffolded {d}: task.json (good = the fix, proof bug = its parent) and a draft plan.md")
    print("next: build both APKs, write the checkpoints and flow, set the bug's expect, approve, prove")
    return 0


def cmd_retro(args) -> int:
    from .retro import retro
    print(retro(args.paths), end="")
    return 0


def cmd_report(args) -> int:
    print(render(load_record(args.record)))
    return 0


def cmd_publish(args) -> int:
    print(publish(args.record, Path(args.repo), push=args.push, video=args.with_video, max_open=args.max_open))
    return 0


def cmd_eval(args) -> int:
    from .evals import run_eval, table
    out = Path(args.out or Path(args.dir) / "eval-out" / datetime.now().strftime("%Y%m%d-%H%M%S"))
    out.mkdir(parents=True, exist_ok=True)
    device = _device(args)
    records = run_eval(Path(args.dir), device, _maestro(device), out, good_runs=args.runs, extra=_extra(args),
                       snapshot=args.snapshot)
    text = table(records, args.config)
    (out / "results.md").write_text(text)
    print(text)
    return 0


def cmd_prepare(args) -> int:
    task = load_task(args.task)
    d = _device(args)
    d.free_automation_lock()
    d.install(task.good)
    d.reset(task.app_id, task.device.grants, task.device.dnd_access)
    if task.device.clock:
        d.pin_clock(task.device.clock, task.device.timezone or "UTC")
    print(f"{task.app_id} good build installed and reset on {d.serial}"
          + (f"; clock pinned to {task.device.clock}" if task.device.clock else "")
          + ". Run 'proofloop restore-clock' when done exploring.")
    return 0


def cmd_restore_clock(args) -> int:
    _device(args).restore_clock()
    print("automatic time restored")
    return 0


def cmd_probe(args) -> int:
    print(json.dumps(_device(args).probe()))
    return 0


def cmd_doctor(args) -> int:
    ok = True
    def line(good, msg):
        nonlocal ok
        ok &= good
        print(("ok    " if good else "FAIL  ") + msg)
    line(bool(shutil.which("maestro")), "maestro CLI on PATH" + ("" if shutil.which("maestro") else
         " (brew tap mobile-dev-inc/tap && brew install mobile-dev-inc/tap/maestro)"))
    try:
        d = _device(args)
        line(True, f"device {d.serial}: {d.facts()['model']} Android {d.facts()['android']}")
        free = d.free_mb()
        line(free >= d.MIN_FREE_MB, f"{free} MB free on /data (need {d.MIN_FREE_MB})")
    except Exception as e:  # doctor reports, it does not crash
        line(False, str(e))
    return 0 if ok else 2


def _app_dir(task):
    d = task.dir.parent
    return d if (d / "app-map.md").exists() else None


def _learn_proof(app_dir, out) -> str:
    from .learn import Memory, runs_from_record_dir
    mem = Memory(app_dir)
    sid, build, runs, when = runs_from_record_dir(out)
    if mem.ingest_session(sid, build, runs, when):
        mem.ingest_flaky(sid, build, runs)
    mem.save()
    (app_dir / "learned.md").write_text(mem.render())
    return f"learned from {len(runs)} good runs into {app_dir / 'learned.md'}"


def cmd_try(args) -> int:
    """One run on the good build, kept as an authoring attempt and fed to the app memory."""
    from .learn import Memory, runs_from_attempts
    from .verify import run_once
    task = load_task(args.task)
    result, flows = check_task_flows(task)
    if not result.ok:
        for e in result.errors:
            print(f"ERROR {e}")
        print("fix the flow check first (proofloop check)")
        return 1
    d = _device(args)
    d.free_automation_lock()
    d.install(task.good)
    out = task.dir / "attempts" / datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        r = run_once(task, flows, d, _maestro(d), "good", 1, out)
    finally:
        if task.device.clock:
            d.restore_clock()
    build = Path(task.good).stem
    (out / "attempt.json").write_text(json.dumps({"task": task.name, "build": build, "passed": r.passed,
                                                  "checkpoint": r.checkpoint, "step": r.step, "error": r.error}, indent=1))
    print("PASS" if r.passed else f"FAIL at {r.checkpoint} ({r.step}): {r.error}")
    app = _app_dir(task)
    if app and not r.environment:
        mem = Memory(app)
        mem.ingest_session(f"attempt:{task.name}@{out.name}", build, runs_from_attempts([out]), out.name)
        mem.save()
        (app / "learned.md").write_text(mem.render())
        print(f"memory updated: {app / 'learned.md'}")
    return 0 if r.passed else 1


def cmd_learn(args) -> int:
    from .learn import Memory, is_bug_or_scoring_run, runs_from_attempts
    app = Path(args.app_dir)
    mem = Memory(app)
    n = 0
    for p in args.proof or []:
        print(_learn_proof(app, Path(p)))
        mem = Memory(app)
    if args.maestro_tests:
        if not args.build:
            raise ValueError("--maestro-tests needs --build (the good build those runs used)")
        dirs = []
        for d in sorted(Path(args.maestro_tests).iterdir()):
            log = (d / "maestro.log").read_text(errors="ignore") if (d / "maestro.log").exists() else ""
            if args.match in log and not is_bug_or_scoring_run(log) and any(d.glob("*/commands.json")):
                dirs.append(d)
        for d in dirs:
            n += mem.ingest_session(f"maestro:{d.name}", args.build, runs_from_attempts([d]), d.name)
    for t in args.attempts or []:
        for d in sorted((Path(t) / "attempts").iterdir()):
            meta = json.loads((d / "attempt.json").read_text()) if (d / "attempt.json").exists() else {}
            n += mem.ingest_session(f"attempt:{t}@{d.name}", meta.get("build", ""), runs_from_attempts([d]), d.name)
    if args.current_build:
        mem.current_build = args.current_build
    mem.save()
    (app / "learned.md").write_text(mem.render())
    print(f"{n} new sources; {len(mem.facts)} facts; wrote {app / 'learned.md'}")
    return 0


def cmd_map(args) -> int:
    from .appmap import ambiguous_anchors, check, coverage, load, unreachable
    m = load(args.map)
    errs = check(m)
    n_edges = sum(len(s.edges) for s in m.screens.values())
    n_notes = sum(len(s.notes) for s in m.screens.values())
    print(f"{m.app}: {len(m.screens)} screens, {n_edges} actions, {n_notes} notes, {len(m.routes)} routes")
    for e in errs:
        print(f"ERROR {e}")
    amb = ambiguous_anchors(m)
    for (sid, a), others in amb.items():
        print(f"WARN  anchor \"{a}\" of '{sid}' is also on {', '.join(others)}; it cannot identify the screen "
              "(the learner ignores it)")
    for s in m.screens.values():
        if s.anchors and all((s.id, a) in amb for a in s.anchors):
            print(f"WARN  screen '{s.id}' has no anchor unique to it; add text only this screen shows")
    for s in unreachable(m):
        print(f"FLAG  screen '{s}' is not reachable from '{next(iter(m.screens))}'")
    if args.flows:
        files = [f for p in map(Path, args.flows) for f in ([p] if p.is_file() else sorted(p.rglob("*.yaml")))]
        cov = coverage(m, [f.read_text() for f in files])
        for kind in ("screens", "edges"):
            hit = [k for k, v in cov[kind].items() if v]
            print(f"{kind}: {len(hit)}/{len(cov[kind])} covered by {len(files)} flows")
            for k, v in cov[kind].items():
                if not v:
                    print(f"  not covered: {k}")
    print("ok" if not errs else "not ok")
    return 0 if not errs else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="proofloop", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--device", help="adb serial (default: the only connected device)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("check"); s.add_argument("task")
    s.add_argument("--fix", action="store_true", help="apply the fixes with one right answer (launchApp options, "
                   "marker above its gating wait), then check"); s.set_defaults(fn=cmd_check)
    s = sub.add_parser("approve", help="bind a human's approval to the current plan.md")
    s.add_argument("task"); s.add_argument("--by", required=True, help="who approved the plan")
    s.set_defaults(fn=cmd_approve)
    s = sub.add_parser("prove"); s.add_argument("task"); s.add_argument("--out"); s.add_argument("--runs", type=int)
    s.add_argument("--fail-fast", action="store_true", help="stop good runs at the first failure")
    s.add_argument("--devices", help="more device serials, comma-separated: good runs 2..N are spread over them")
    s.add_argument("--snapshot", help="emulator snapshot to load on every device before the proof")
    s.add_argument("--no-video", dest="video", action="store_false", help="do not record good run 1")
    s.add_argument("--no-learn", dest="learn", action="store_false", help="do not update the app memory"); s.set_defaults(fn=cmd_prove)
    s = sub.add_parser("try"); s.add_argument("task"); s.set_defaults(fn=cmd_try)
    s = sub.add_parser("learn"); s.add_argument("app_dir")
    s.add_argument("--proof", action="append", help="proof output dir (record.json + good-* runs); repeatable")
    s.add_argument("--attempts", action="append", help="task dir whose attempts/ to ingest; repeatable")
    s.add_argument("--maestro-tests", help="import authoring runs from a Maestro tests dir (~/.maestro/tests)")
    s.add_argument("--match", default="", help="with --maestro-tests: only runs whose maestro.log mentions this")
    s.add_argument("--build", help="with --maestro-tests: the good build those runs used")
    s.add_argument("--current-build", help="the app's current good build, for staleness (default: build of the latest run)")
    s.set_defaults(fn=cmd_learn)
    s = sub.add_parser("report"); s.add_argument("record"); s.set_defaults(fn=cmd_report)
    s = sub.add_parser("history", help="proof history and shelf life of a task's test")
    s.add_argument("task"); s.set_defaults(fn=cmd_history)
    s = sub.add_parser("mine-bugs", help="list fix commits whose parent can serve as a real held-out bug")
    s.add_argument("repo"); s.add_argument("--task", help="rank by overlap with this task's criterion")
    s.add_argument("--limit", type=int, default=15); s.add_argument("--since"); s.set_defaults(fn=cmd_mine)
    s = sub.add_parser("retro", help="group rejected proofs by cause and name the rule or step for each")
    s.add_argument("paths", nargs="+"); s.set_defaults(fn=cmd_retro)
    s = sub.add_parser("next", help="backfill queue: app-map rules, screens and actions no flow covers yet")
    s.add_argument("app_dir"); s.add_argument("--limit", type=int, default=15); s.set_defaults(fn=cmd_next)
    s = sub.add_parser("from-fix", help="scaffold a regression-test task from a fix commit (good = fix, bug = parent)")
    s.add_argument("repo"); s.add_argument("sha"); s.add_argument("--app-dir", required=True)
    s.add_argument("--name", required=True); s.set_defaults(fn=cmd_from_fix)
    s = sub.add_parser("publish"); s.add_argument("record"); s.add_argument("--repo", required=True)
    s.add_argument("--push", action="store_true", help="push and open a PR with gh")
    s.add_argument("--with-video", action="store_true", help="commit the recording of good run 1 next to the flow")
    s.add_argument("--max-open", type=int, default=3,
                   help="with --push: refuse while this many proofloop/* PRs are open (review capacity)")
    s.set_defaults(fn=cmd_publish)
    s = sub.add_parser("eval"); s.add_argument("dir"); s.add_argument("--out"); s.add_argument("--config", default="")
    s.add_argument("--runs", type=int, help="override good_runs (3 for provisional dev sweeps)")
    s.add_argument("--devices", help="more device serials for good runs, comma-separated")
    s.add_argument("--snapshot", help="emulator snapshot to load before each proof"); s.set_defaults(fn=cmd_eval)
    s = sub.add_parser("prepare"); s.add_argument("task"); s.set_defaults(fn=cmd_prepare)
    s = sub.add_parser("restore-clock"); s.set_defaults(fn=cmd_restore_clock)
    s = sub.add_parser("probe"); s.set_defaults(fn=cmd_probe)
    s = sub.add_parser("doctor"); s.set_defaults(fn=cmd_doctor)
    s = sub.add_parser("map"); s.add_argument("map"); s.add_argument("flows", nargs="*"); s.set_defaults(fn=cmd_map)
    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except (TaskError, ValueError, FileNotFoundError, DeviceError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
