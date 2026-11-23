"""Verifier: run a task's steps on the good build and on each bug build, then compute the verdict.

The verdict is plain code over run results:
  blocked_policy       a flow uses a blocked command or targets another app
  needs_human          the flows cannot be checked (e.g. a checkpoint with no assertion)
  blocked_environment  the device or Maestro failed; not evidence about the test
  budget_exhausted     the time budget ran out before the proof finished
  rejected_flaky       fewer than good_runs passes on the good build
  rejected_missed_bug  a proof bug passed, or failed somewhere other than its expected checkpoint
  proven               every good run passed and every proof bug failed at its expected checkpoint
Held-out bugs run after the verdict and never change it.

Run order: one good run, then every proof bug, then the remaining good runs. A test that misses a
proof bug is rejected after about two runs, and the remaining good runs are skipped.
The record keeps a sha256 of every file the proof used (task, plan, flows, APKs), so a published
test can be checked against what was actually proven.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, time as clock_time
from pathlib import Path

from . import RECORD_SCHEMA_VERSION, __version__
from .device import DeviceError
from .flow import check_task_flows
from .label import label_record
from .task import file_sha256

POLICY_MARKERS = ("blocked command", "targets another app", "force-stops the app", "clearState", "must set stopApp")
POLL_S = 1.0  # probe polling interval; tests set it to 0


@dataclass
class RunResult:
    build: str
    run: int
    passed: bool
    checkpoint: str | None = None  # failing checkpoint id, or "setup" / "action"
    step: str = ""  # the failing step, e.g. 'flow.yaml:44 assertVisible' or 'probe E2'
    error: str = ""
    environment: bool = False
    seconds: float = 0.0
    evidence: str = ""
    probes: list = field(default_factory=list)
    device: str = ""  # serial of the device that ran it (good runs can be spread over several)


def flake_upper_bound(passes: int, runs: int) -> float | None:
    """95% upper bound on the true failure rate when all runs passed (exact binomial)."""
    if runs == 0 or passes != runs:
        return None
    return 1 - 0.05 ** (1 / runs)


def run_once(task, flows, device, maestro, build: str, n: int, out_root: Path) -> RunResult:
    t0 = time.monotonic()
    res = RunResult(build, n, passed=False, device=getattr(device, "serial", ""))
    reached = False  # a checkpoint has been reached in this run

    def fail(checkpoint, step, error, env=False, evidence=""):
        res.checkpoint = checkpoint if checkpoint else ("action" if reached else "setup")
        res.step, res.error, res.environment, res.evidence = step, error, env, evidence
        res.seconds = round(time.monotonic() - t0, 1)
        return res

    try:
        device.reset(task.app_id, task.device.grants, task.device.dnd_access)
        if task.device.clock:
            device.pin_clock(task.device.clock, task.device.timezone or "UTC")
        for i, step in enumerate(task.steps, 1):
            kind, val = next(iter(step.items()))
            if kind == "flow":
                path = task.dir / val
                flow = flows[str(path)]
                r = maestro.run(path, out_root / f"{build}-{n}" / f"step{i}-{path.stem}")
                if not r.passed:
                    if r.environment:
                        return fail(None, f"{path.name}", r.error, env=True, evidence=r.evidence)
                    cmd = flow.commands[r.failed_index] if r.failed_index is not None and r.failed_index < len(flow.commands) else None
                    where = f"{path.name}:{cmd.line} {cmd.name}" if cmd else path.name
                    reached = reached or any(c.checkpoint for c in flow.commands[:r.failed_index or 0])
                    return fail(flow.checkpoint_of(r.failed_index), where, r.error, evidence=r.evidence)
                reached = reached or any(c.checkpoint for c in flow.commands)
            elif kind == "set_clock":
                device.set_clock(clock_time.fromisoformat(val))
            elif kind == "wait_clock":
                device.wait_clock(clock_time.fromisoformat(val))
            elif kind == "probe":
                p = _probe(device, val, task)
                res.probes.append({"checkpoint": val["checkpoint"], **p})
                if p["state"] != val["expect"]:
                    return fail(val["checkpoint"], f"probe {val['checkpoint']}",
                                f"expected {val['expect']}, read {p}")
                reached = True
    except DeviceError as e:
        return fail(None, "environment", str(e), env=True)
    res.passed = True
    res.seconds = round(time.monotonic() - t0, 1)
    return res


def _probe(device, spec, task) -> dict:
    if "until" not in spec:
        return device.probe()
    until = datetime.combine(task.device.clock.date(), clock_time.fromisoformat(spec["until"]))
    while True:
        p = device.probe()
        if p["state"] == spec["expect"] or device.now() >= until:
            return p
        time.sleep(POLL_S)


def prove(task, device, maestro, out_root: Path, fail_fast: bool = False, extra=(), snapshot: str | None = None,
          video: bool = True) -> dict:
    """Run the proof and return the run record (a plain dict, ready for JSON).

    extra: more (device, maestro) pairs; good runs 2..N are spread over all devices in parallel. Bug
    builds always run on the main device. snapshot: emulator snapshot loaded on every device first, so
    each proof starts from the same device image (clock, do-not-disturb, free space). video: record good
    run 1 on the main device for reviewers.
    """
    started = datetime.now().isoformat(timespec="seconds")
    t0 = time.monotonic()
    out_root = Path(out_root)
    check, flows = check_task_flows(task)
    record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "proofloop_version": __version__,
        "task": task.name,
        "criterion": task.criterion,
        "task_file": str(task.path),
        "flows": [str(p) for p in task.flow_paths()],
        "started": started,
        "flow_check": {"errors": check.errors, "coordinate_fallbacks": check.fallbacks},
        "repairs": task.repairs,
        "good": {"apk": str(task.good), "runs": [], "required": task.good_runs},
        "bugs": [],
        "environment": {},
        # every input the proof used, by path; publish refuses a flow whose hash no longer matches
        "artifacts": {str(p): file_sha256(p) for p in
                      [task.path, task.plan_path, *task.flow_paths(), task.good, *(b.apk for b in task.bugs)]},
    }

    def finish(verdict, reason):
        record["verdict"], record["reason"] = verdict, reason
        record["seconds"] = round(time.monotonic() - t0, 1)
        good = record["good"]
        good["passes"] = sum(r["passed"] for r in good["runs"])
        good["flake_upper_bound_95"] = flake_upper_bound(good["passes"], len(good["runs"]))
        record["failure_label"] = label_record(record)
        return record

    record["approved_by"] = task.approved_by
    record["approved_plan"] = task.approved_plan
    record["author"] = dict(task.author)
    if task.author.get("session"):
        from .cost import session_usage
        record["author_usage"] = session_usage(task.author["session"])
    declared = {cp for f in flows.values() for cp in f.checkpoints} | set(task.probe_checkpoints())
    problem = task.approval_problem(declared)
    if problem:
        return finish("needs_human", problem)
    if not check.ok:
        policy = any(m in e for e in check.errors for m in POLICY_MARKERS)
        return finish("blocked_policy" if policy else "needs_human", "; ".join(check.errors))

    over_budget = lambda: task.budget_minutes is not None and time.monotonic() - t0 > task.budget_minutes * 60
    pool = [(device, maestro), *extra]
    try:
        for d, _ in pool:
            if snapshot:
                d.load_snapshot(snapshot)
            d.free_automation_lock()
        record["environment"] = device.facts()
        if snapshot:
            record["environment"]["snapshot"] = snapshot
        if extra:
            record["environment"]["extra_devices"] = [d.facts() for d, _ in extra]

        def run_good(d, m, numbers):
            """Good runs on one device. Returns (runs, stop) where stop is None, "stop", or a reason."""
            runs = []
            for n in numbers:
                if over_budget():
                    return runs, ("budget_exhausted", f"time budget of {task.budget_minutes} min ran out at good run {n}")
                r = run_once(task, flows, d, m, "good", n, out_root)
                runs.append(asdict(r))
                if r.environment:
                    return runs, ("blocked_environment", f"good run {n}: {r.error}")
                if not r.passed and fail_fast:
                    return runs, "stop"
            return runs, None

        def good_runs(numbers):
            """Run good-build runs over the device pool. Returns a finished record, "stop" (fail-fast), or None."""
            numbers = list(numbers)
            shares = [(d, m, numbers[i::len(pool)]) for i, (d, m) in enumerate(pool) if numbers[i::len(pool)]]

            def work(d, m, ns):
                d.install(task.good)
                return run_good(d, m, ns)
            if len(shares) == 1:
                results = [work(*shares[0])]
            else:
                with ThreadPoolExecutor(len(shares)) as ex:
                    results = list(ex.map(lambda s: work(*s), shares))
            record["good"]["runs"] += sorted((r for runs, _ in results for r in runs), key=lambda r: r["run"])
            for _, stop in results:
                if isinstance(stop, tuple):
                    return finish(*stop)
            return "stop" if any(stop == "stop" for _, stop in results) else None

        device.install(task.good)
        recording = video and hasattr(device, "start_recording")
        if recording:
            try:
                device.start_recording()
            except DeviceError:
                recording = False
        first = run_good(device, maestro, [1])
        record["good"]["runs"] += first[0]
        if recording:
            try:
                (out_root / "good-1").mkdir(parents=True, exist_ok=True)
                record["good"]["video"] = device.stop_recording(out_root / "good-1" / "run.mp4")
            except (DeviceError, OSError):
                pass  # evidence only; never changes a verdict
        if isinstance(first[1], tuple):
            return finish(*first[1])
        first = first[1]

        caught_all, missed = True, []
        for bug in [b for b in task.bugs if b.role == "proof"]:
            if over_budget():
                return finish("budget_exhausted", f"time budget ran out before proof bug {bug.name}")
            device.install(bug.apk)
            r = run_once(task, flows, device, maestro, bug.name, 1, out_root)
            if r.environment:
                return finish("blocked_environment", f"proof bug {bug.name}: {r.error}")
            caught = (not r.passed) and r.checkpoint == bug.expect
            record["bugs"].append({"name": bug.name, "role": "proof", "expect": bug.expect, "caught": caught,
                                   "result": asdict(r)})
            if not caught:
                caught_all = False
                missed.append(f"{bug.name} " + ("passed" if r.passed else f"failed at {r.checkpoint}, expected {bug.expect}"))

        first_passed = record["good"]["runs"][0]["passed"]
        if task.good_runs > 1:
            # Skip only when run 1 passed: after a good-build failure, the full set of runs is what lets the
            # labeller tell a flake from a real bug (one run would read as "fails every time").
            if not caught_all and first_passed:
                record["good"]["skipped"] = f"good runs 2-{task.good_runs} skipped: a proof bug was missed"
            elif first != "stop":
                rest = good_runs(range(2, task.good_runs + 1))
                if isinstance(rest, dict):
                    return rest

        runs = record["good"]["runs"]
        passes = sum(x["passed"] for x in runs)
        if passes < len(runs) or (caught_all and passes < task.good_runs):
            verdict, reason = "rejected_flaky", f"good build passed {passes}/{task.good_runs}"
        elif not caught_all:
            verdict, reason = "rejected_missed_bug", "; ".join(missed)
            if "skipped" in record["good"]:
                reason += f" ({record['good']['skipped']})"
        else:
            verdict, reason = "proven", f"passed {passes}/{task.good_runs}; every proof bug failed at its expected checkpoint"

        for bug in [b for b in task.bugs if b.role == "held_out"]:
            if over_budget():
                break
            device.install(bug.apk)
            r = run_once(task, flows, device, maestro, bug.name, 1, out_root)
            caught = (not r.passed) and not r.environment and r.checkpoint not in ("setup", "action")
            record["bugs"].append({"name": bug.name, "role": "held_out", "expect": None, "caught": caught,
                                   "result": asdict(r)})
        return finish(verdict, reason)
    except DeviceError as e:
        return finish("blocked_environment", str(e))
    finally:
        for d, _ in pool:
            try:
                d.install(task.good)
            except DeviceError:
                pass
            d.restore_clock()
