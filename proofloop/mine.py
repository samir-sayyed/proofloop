"""Mine real bugs from an app's git history: the commit before a fix is a real, unseeded bug build.

Six of the seven bugs in this repo's eval were hand-written by the person who built the tool. A fix
commit's parent reintroduces a defect nobody wrote for the test. Used as a held-out bug, it measures
whether a proven test catches a regression it was not tuned for. (Mutation-style held-out checks,
AI Engineer 2026: Knox's outer loop, Pocock's tests that certify the wrong thing.)

ponytail: commit-message heuristics plus word overlap with the task's criterion. Upgrade path: link
fixes to issue trackers, or bisect from a failing test.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

FIX_RE = r"\b(fix(es|ed)?|bug|crash|regress(ion)?|broken|wrong|incorrect)\b"
TEST_PATH = re.compile(r"(^|/)(test|androidTest|tests?)/|Test\.(kt|java|swift)$", re.I)
SOURCE = re.compile(r"\.(kt|java|swift|ts|tsx|js|dart|xml)$")
STOP = set("a an and the of to in on for with is it its as by at from that this be are was when after before "
           "shows show lists list into".split())


def _git(repo, *args) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{3,}", re.sub(r"([a-z])([A-Z])", r"\1 \2", text).lower()) if w not in STOP}


def fix_commits(repo, criterion: str = "", limit: int = 15, since: str | None = None, after: str | None = None) -> list[dict]:
    """Candidate fix commits, best first: source-only, small, and (with a criterion) on topic.

    after: only fixes whose parent already contains this commit (the task's good build). Otherwise the parent
    can lack other, older fixes and be "caught" for a bug it was not mined for.
    """
    args = ["log", "--no-merges", "-i", "-E", "--grep=(fix|bug|crash|regress|broken|wrong|incorrect)", "--format=%H%x09%P%x09%ad%x09%s", "--date=short"]
    if since:
        args.append(f"--since={since}")
    want = words(criterion)
    out = []
    for line in _git(repo, *args).splitlines():
        sha, parents, date, subject = line.split("\t", 3)
        if " " in parents or not parents or not re.search(FIX_RE, subject, re.I):
            continue  # merges, roots, and words like "prefix" or "debugging"
        files = [f for f in _git(repo, "show", "--name-only", "--format=", sha).splitlines() if f]
        src = [f for f in files if SOURCE.search(f) and not TEST_PATH.search(f)]
        if not src:
            continue  # docs, build or test-only change: its parent is not a behaviour bug
        if after and subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", after, parents],
                                    capture_output=True).returncode != 0:
            continue  # the parent predates the good build: it differs by more than this bug
        overlap = sorted(want & (words(subject) | {w for f in src for w in words(Path(f).stem)}))
        score = 3 * len(overlap) - min(len(src), 10) / 3 + (1 if any(t in f for f in src for t in ("ui/", "Screen", "ViewModel")) else 0)
        out.append({"sha": sha[:10], "parent": parents[:10], "date": date, "subject": subject, "files": len(src),
                    "overlap": overlap, "score": round(score, 1)})
    return sorted(out, key=lambda c: -c["score"])[:limit]
