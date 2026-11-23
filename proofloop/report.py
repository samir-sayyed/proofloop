"""Human-readable report and pull request publisher. Both read only the run record."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .task import file_sha256

VERDICT_TEXT = {
    "proven": "Proven",
    "rejected_flaky": "Rejected: flaky on the good build",
    "rejected_missed_bug": "Rejected: did not catch a proof bug at its expected checkpoint",
    "blocked_environment": "Blocked: device or tool failure (not evidence about the test)",
    "blocked_policy": "Blocked: the flow uses a command outside the allowlist",
    "budget_exhausted": "Stopped: time budget ran out",
    "needs_human": "Needs a human: no approval covers this plan, or the flow cannot be checked",
}


def load_record(path) -> dict:
    return json.loads(Path(path).read_text())


def render(record: dict) -> str:
    g = record["good"]
    lines = [f"# {VERDICT_TEXT.get(record['verdict'], record['verdict'])}: {record['task']}", "",
             f"**Criterion:** {record['criterion']}", "",
             f"**Verdict:** `{record['verdict']}`. {record.get('reason', '')}", ""]
    if record["verdict"] != "proven":
        lines += ["This test is not proven. Do not treat it as protecting the criterion.", ""]
    runs = g.get("runs", [])
    if runs:
        bound = g.get("flake_upper_bound_95")
        lines.append(f"**Good build:** passed {g.get('passes', 0)}/{len(runs)} clean runs"
                     + (f". With no failures in {len(runs)} runs, the true flake rate could still be up to "
                        f"{bound:.0%} (95% confidence)." if bound is not None else "."))
        lines += ["", "| Run | Result | Checkpoint | Step | Seconds |", "|---|---|---|---|---|"]
        for r in runs:
            lines.append(f"| {r['run']} | {'pass' if r['passed'] else 'FAIL'} | {r['checkpoint'] or ''} | "
                         f"{r['step'] or ''} | {r['seconds']} |")
        lines.append("")
        if g.get("skipped"):
            lines += [f"_{g['skipped']}._", ""]
    if record["bugs"]:
        lines += ["**Seeded bugs:**", "", "| Bug | Role | Expected checkpoint | Failed at | Caught | Evidence |",
                  "|---|---|---|---|---|---|"]
        for b in record["bugs"]:
            r = b["result"]
            failed_at = "passed" if r["passed"] else (r["checkpoint"] or "")
            lines.append(f"| {b['name']} | {b['role'].replace('_', '-')} | {b['expect'] or 'any'} | {failed_at} | "
                         f"{'yes' if b['caught'] else 'NO'} | {r.get('evidence', '')} |")
        lines += ["", "Held-out bugs are run after the verdict and never change it.", ""]
    fc = record.get("flow_check", {})
    if fc.get("errors"):
        lines += ["**Flow check errors:**", ""] + [f"- {e}" for e in fc["errors"]] + [""]
    lines += ["**Coordinate fallbacks:** " + str(len(fc.get("coordinate_fallbacks", [])))]
    lines += [f"- {f}" for f in fc.get("coordinate_fallbacks", [])] + [""]
    if record.get("repairs"):
        lines += ["**Repairs made before this proof:**", ""]
        lines += [f"- {r.get('reason', '')}: {r.get('change', '')}" for r in record["repairs"]] + [""]
    if record.get("artifacts"):
        lines += ["**Proven against** (sha256, first 12 hex):", ""]
        lines += [f"- `{Path(p).name}`: " + (f"`{h[7:19]}`" if h else "missing")
                  for p, h in record["artifacts"].items()] + [""]
    if g.get("video"):
        lines += [f"**Video of good run 1:** {g['video']}", ""]
    env = record.get("environment", {})
    extra = env.get("extra_devices", [])
    lines += [f"**Duration:** {record.get('seconds', 0) / 60:.1f} min. **Failure label:** `{record.get('failure_label')}`.",
              f"**Device:** {env.get('model', '?')}, Android {env.get('android', '?')}, host {env.get('host', '?')}"
              + (f", plus {len(extra)} more for good runs" if extra else "")
              + (f", from snapshot `{env['snapshot']}`" if env.get("snapshot") else "") + ".",
              f"**Approved by:** {record.get('approved_by') or 'nobody'}.",
              f"**Authored by:** {author_line(record)}.", "",
              "Humans merge. ProofLoop never merges its own pull requests."]
    return "\n".join(lines) + "\n"


def author_line(record: dict) -> str:
    a, u = record.get("author") or {}, record.get("author_usage")
    who = ", ".join(str(a[k]) for k in ("agent", "model") if a.get(k)) or "not recorded"
    if u:
        return f"{who}; {u['total'] / 1000:.1f}k tokens ({u['output'] / 1000:.1f}k output, {u['requests']} requests)"
    if a.get("tokens"):
        return f"{who}; {int(a['tokens']) / 1000:.1f}k tokens (reported)"
    return who + "; model cost not measured (no author session in task.json)"


def open_proofloop_prs(repo: Path) -> int:
    out = subprocess.run(["gh", "pr", "list", "--state", "open", "--json", "headRefName", "--limit", "200"],
                         cwd=repo, check=True, capture_output=True, text=True).stdout
    return sum(p["headRefName"].startswith("proofloop/") for p in json.loads(out))


def publish(record_path, repo: Path, push: bool = False, video: bool = False, max_open: int = 3) -> str:
    """Copy the proven flows into the app repo on a new branch and commit them.

    With push=True, also push the branch and open a pull request with gh, unless max_open proofloop
    PRs are already waiting: reviews, not generation, are the scarce resource. Refuses any record that
    is not proven: an unproven test never opens a normal pull request.
    """
    record = load_record(record_path)
    if record["verdict"] != "proven":
        raise ValueError(f"refusing to publish: verdict is {record['verdict']}, not proven")
    artifacts = record.get("artifacts")
    if not artifacts:
        raise ValueError("refusing to publish: the record has no artifact hashes (made before record schema 2); "
                         "run proofloop prove again")
    for f in record["flows"]:
        if file_sha256(f) != artifacts.get(f):
            raise ValueError(f"refusing to publish: {Path(f).name} changed since it was proven; run proofloop prove again")
    repo = Path(repo).resolve()
    slug = record["task"].replace("/", "-")
    branch = f"proofloop/{slug}"
    dest = repo / ".maestro" / "proofloop" / slug
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout
    if git("status", "--porcelain", "--", ".maestro"):
        raise ValueError(".maestro has uncommitted changes; commit or stash them first")
    if push and max_open and (n := open_proofloop_prs(repo)) >= max_open:
        raise ValueError(f"refusing to open another PR: {n} proofloop PRs are already open (max {max_open}); "
                         "get those reviewed first or raise --max-open")
    git("switch", "-c", branch)
    dest.mkdir(parents=True, exist_ok=True)
    for f in record["flows"]:
        shutil.copy(f, dest / Path(f).name)
    vid = record["good"].get("video")
    if video:
        if not vid or not Path(vid).is_file():
            raise ValueError("--with-video: the record has no recording of good run 1")
        shutil.copy(vid, dest / "good-run.mp4")
    (dest / "proofloop-report.md").write_text(render(record))
    git("add", str(dest))
    git("commit", "-m", f"Add proven UI test: {record['task']}\n\n{record['criterion']}\n\n{record['reason']}")
    if push:
        git("push", "-u", "origin", branch)
        out = subprocess.run(["gh", "pr", "create", "--title", f"Proven UI test: {record['task']}",
                              "--body-file", str(dest / "proofloop-report.md")],
                             cwd=repo, check=True, capture_output=True, text=True).stdout
        return out.strip()
    return f"committed on branch {branch} in {repo} (not pushed)"
