"""proofloop command line.

  proofloop check  TASK            check flows: allowlist, checkpoints, coordinate fallbacks
  proofloop prove  TASK [--out D]  run the proof on a device and write the run record and report
  proofloop report RECORD          print the report for a run record
  proofloop publish RECORD --repo PATH [--push]   commit a proven test to the app repo (and open a PR)
  proofloop eval   DIR [--config NAME] [--runs N] prove every task under DIR and print a results table
  proofloop prepare TASK           install the good build, reset the app, pin the clock (start state for exploring)
  proofloop probe                  print the device sound state (read-only)
  proofloop doctor                 check adb, device, Maestro and free space
  proofloop map    MAP [FLOWS...]  check an app map; with flow files or dirs, report screens/actions no flow covers

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
from .task import TaskError, load_task


def _device(args):
    from .device import AdbDevice
    return AdbDevice(args.device)


def _maestro(device):
    from .maestro import MaestroRunner
    return MaestroRunner(device.serial)


def cmd_check(args) -> int:
    task = load_task(args.task)
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
    print("ok" if result.ok else "not ok")
    return 0 if result.ok else 1


def cmd_prove(args) -> int:
    from .verify import prove
    task = load_task(args.task)
    if args.runs:
        task.good_runs = args.runs
    out = Path(args.out or task.dir / "proofloop-out" / datetime.now().strftime("%Y%m%d-%H%M%S"))
    out.mkdir(parents=True, exist_ok=True)
    device = _device(args)
    record = prove(task, device, _maestro(device), out, fail_fast=args.fail_fast)
    (out / "record.json").write_text(json.dumps(record, indent=2))
    (out / "report.md").write_text(render(record))
    print(render(record))
    print(f"record: {out / 'record.json'}")
    return 0 if record["verdict"] == "proven" else 1


def cmd_report(args) -> int:
    print(render(load_record(args.record)))
    return 0


def cmd_publish(args) -> int:
    print(publish(args.record, Path(args.repo), push=args.push))
    return 0


def cmd_eval(args) -> int:
    from .evals import run_eval, table
    out = Path(args.out or Path(args.dir) / "eval-out" / datetime.now().strftime("%Y%m%d-%H%M%S"))
    out.mkdir(parents=True, exist_ok=True)
    device = _device(args)
    records = run_eval(Path(args.dir), device, _maestro(device), out, good_runs=args.runs)
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


def cmd_map(args) -> int:
    from .appmap import check, coverage, load, unreachable
    m = load(args.map)
    errs = check(m)
    n_edges = sum(len(s.edges) for s in m.screens.values())
    n_notes = sum(len(s.notes) for s in m.screens.values())
    print(f"{m.app}: {len(m.screens)} screens, {n_edges} actions, {n_notes} notes, {len(m.routes)} routes")
    for e in errs:
        print(f"ERROR {e}")
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
    s = sub.add_parser("check"); s.add_argument("task"); s.set_defaults(fn=cmd_check)
    s = sub.add_parser("prove"); s.add_argument("task"); s.add_argument("--out"); s.add_argument("--runs", type=int)
    s.add_argument("--fail-fast", action="store_true", help="stop good runs at the first failure"); s.set_defaults(fn=cmd_prove)
    s = sub.add_parser("report"); s.add_argument("record"); s.set_defaults(fn=cmd_report)
    s = sub.add_parser("publish"); s.add_argument("record"); s.add_argument("--repo", required=True)
    s.add_argument("--push", action="store_true", help="push and open a PR with gh"); s.set_defaults(fn=cmd_publish)
    s = sub.add_parser("eval"); s.add_argument("dir"); s.add_argument("--out"); s.add_argument("--config", default="")
    s.add_argument("--runs", type=int, help="override good_runs (3 for provisional dev sweeps)"); s.set_defaults(fn=cmd_eval)
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
