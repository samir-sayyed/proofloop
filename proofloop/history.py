"""Proof history: one line per proof in <task>/proof-history.jsonl, so a test's shelf life is visible.

A test proven once can stop protecting the criterion when the app changes. Re-proving on each new
good build and keeping the verdicts answers: on how many builds, over how long, has this test stayed
proven, and on which build did it first stop? (Shelf-life-of-code metric from Factory's AI Engineer
2026 talk.)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

NAME = "proof-history.jsonl"


def append(task, record: dict, record_path) -> dict:
    arts = record.get("artifacts") or {}
    flows = "".join(arts.get(f) or "" for f in record.get("flows", []))
    line = {
        "date": record.get("started") or datetime.now().isoformat(timespec="seconds"),
        "verdict": record["verdict"],
        "good_runs": len(record["good"]["runs"]),
        "required": record["good"].get("required"),
        "good": (arts.get(str(task.good)) or "")[7:19],
        "flows": hashlib.sha256(flows.encode()).hexdigest()[:12],
        "record": str(record_path),
    }
    with open(task.dir / NAME, "a") as f:
        f.write(json.dumps(line) + "\n")
    return line


def load(task_dir) -> list[dict]:
    p = Path(task_dir) / NAME
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def summary(rows: list[dict]) -> str:
    if not rows:
        return "no proofs recorded yet"
    full = [r for r in rows if r["good_runs"] >= (r.get("required") or 0)]
    proven = [r for r in rows if r["verdict"] == "proven"]
    if not proven:
        return f"{len(rows)} proofs, never proven"
    first = proven[0]
    builds = sorted({r["good"] for r in proven})
    broke = next((r for r in rows if r["date"] > first["date"] and r["verdict"] != "proven"
                  and r["verdict"] not in ("blocked_environment", "budget_exhausted", "needs_human")), None)
    days = (datetime.fromisoformat((broke or rows[-1])["date"]) - datetime.fromisoformat(first["date"])).days
    text = (f"{len(rows)} proofs ({len(full)} with every good run); first proven {first['date'][:10]}; "
            f"proven on {len(builds)} good build(s)")
    if broke:
        text += f"; stopped being proven on {broke['date'][:10]} (build {broke['good']}: {broke['verdict']}) after {days} days"
    else:
        last = rows[-1]
        text += f"; latest {last['date'][:10]}: {last['verdict']}; shelf life so far {days} days"
    return text
