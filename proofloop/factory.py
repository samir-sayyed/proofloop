"""Feed the proof gate: a backfill queue from the app map, and task scaffolds from real fix commits.

`next` (Duolingo's test backfill, AI Engineer 2026: pick what an agent can test well, keep a queue)
ranks what no proven flow covers yet: app-map rules first (each is a behaviour claim), then screens,
then actions. `from-fix` (Factory and WorkOS: start from a signal) turns a bug-fix commit into a task
whose good build is the fix and whose proof bug is the commit before it: a regression test for a real
bug. Both write drafts only. A plan still needs approval before anything is proven.

ponytail: text matching against flows, like `proofloop map`. A rule counts as covered when every
quoted text in it appears in some flow.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from .appmap import coverage, load

GUIDANCE = re.compile(r"\b(locator|never guessed|read from the app)\b", re.I)  # rules for authors, not app behaviour


def _flows(app_dir: Path) -> list[str]:
    return [p.read_text() for p in sorted(app_dir.glob("*/*.yaml"))]


def backlog(app_dir) -> list[dict]:
    app_dir = Path(app_dir)
    m = load(app_dir / "app-map.md")
    texts = _flows(app_dir)
    blob = "\n".join(texts)
    items = []
    for s in m.screens.values():
        for kind, note in s.notes:
            if kind != "rule" or GUIDANCE.search(note):
                continue
            quoted = re.findall(r'"([^"]+)"', note)
            if quoted and all(q in blob for q in quoted):
                continue
            items.append({"kind": "rule", "screen": s.id, "score": 3 + min(len(quoted), 3),
                          "criterion": f"On {s.id.replace('_', ' ')}: {note}"})
    cov = coverage(m, texts)
    for sid, hit in cov["screens"].items():
        if not hit:
            items.append({"kind": "screen", "screen": sid, "score": 2,
                          "criterion": f"The {sid.replace('_', ' ')} screen opens and shows "
                                       + ", ".join(f'"{a}"' for a in m.screens[sid].anchors)})
    for edge, hit in cov["edges"].items():
        if not hit:
            sid, rest = edge.split(": ", 1)
            items.append({"kind": "action", "screen": sid, "score": 1, "criterion": f"On {sid.replace('_', ' ')}, {rest}"})
    return sorted(items, key=lambda i: -i["score"])


def _git(repo, *a) -> str:
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout


def from_fix(repo, sha: str, app_dir, name: str, apk_dir: str = "../../../.scratch/proofloop/apks") -> Path:
    """Scaffold tasks/<app>/<name>/ for a regression test of a real fix. Returns the task folder."""
    app_dir = Path(app_dir)
    full = _git(repo, "rev-parse", sha).strip()
    parent = _git(repo, "rev-parse", f"{full}^").strip()
    subject = _git(repo, "log", "-1", "--format=%s", full).strip()
    body = _git(repo, "log", "-1", "--format=%b", full).strip()
    stat = _git(repo, "show", "--stat", "--format=", full).strip()
    topic = re.sub(r"^fix(\(.*?\))?:\s*", "", subject, flags=re.I)  # "fix(ui): x" -> "x"
    sibling = next(iter(sorted(app_dir.glob("*/task.json"))), None)
    base = json.loads(sibling.read_text()) if sibling else {}
    d = app_dir / name
    if d.exists():
        raise FileExistsError(f"{d} exists")
    d.mkdir(parents=True)
    task = {
        "name": f"{app_dir.name}/{name}",
        "criterion": f"Regression test for {full[:7]}: {topic}",
        "app_id": base.get("app_id", "TODO.app.id"),
        "good": f"{apk_dir}/good-{full[:7]}.apk",
        "bugs": [{"name": f"pre-fix-{parent[:7]}", "apk": f"{apk_dir}/good-{parent[:7]}.apk", "role": "proof",
                  "expect": "TODO", "note": f"the commit before the fix {full[:7]}; a real bug, not a seeded one"}],
        "device": base.get("device", {}),
        "good_runs": 10,
        "budget_minutes": 30,
        "steps": [{"flow": "flow.yaml"}],
        "source_fix": {"repo": str(Path(repo).resolve()), "fix": full, "parent": parent, "subject": subject},
    }
    (d / "task.json").write_text(json.dumps(task, indent=2) + "\n")
    (d / "plan.md").write_text(
        f"# Plan: {name}\n\nCriterion: {task['criterion']}\n\nFix commit {full[:10]} (parent {parent[:10]}):\n\n"
        f"> {subject}\n" + "".join(f"> {l}\n" for l in body.splitlines()) + f"\n```\n{stat}\n```\n\n"
        "Checkpoints: TODO. Each must be visible on the fix build and broken on the parent build. Set the proof "
        "bug's expect to the checkpoint the parent build should fail at, then get the plan approved.\n")
    return d
