"""Eval runner: prove every task under a directory and write a results table.

Each configuration (for example "loop-to-green" versus "full loop") is a directory of
tasks whose flows that configuration authored. Running the same tasks under several
configuration directories gives a like-for-like comparison.
"""

from __future__ import annotations

import json
from pathlib import Path

from .task import load_task
from .verify import prove


def find_tasks(root: Path) -> list[Path]:
    return sorted(Path(root).glob("**/task.json"))


def run_eval(root: Path, device, maestro, out: Path, good_runs: int | None = None, **prove_kw) -> list[dict]:
    records = []
    for tp in find_tasks(root):
        task = load_task(tp)
        if good_runs:
            task.good_runs = good_runs
        rec = prove(task, device, maestro, out / task.name.replace("/", "-"), **prove_kw)
        (out / f"{task.name.replace('/', '-')}.record.json").write_text(json.dumps(rec, indent=2))
        records.append(rec)
    return records


def table(records: list[dict], config: str = "") -> str:
    rows = ["| Task | Verdict | Good passes | Proof bugs caught | Held-out caught | Fallbacks | Repairs | Author | "
            "Author tokens | Minutes |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    tot = {"tasks": 0, "proven": 0, "proof": 0, "proof_caught": 0, "held": 0, "held_caught": 0, "runs": 0, "passes": 0,
           "repairs": 0, "tokens": 0, "minutes": 0.0}
    for r in records:
        proof = [b for b in r["bugs"] if b["role"] == "proof"]
        held = [b for b in r["bugs"] if b["role"] == "held_out"]
        g = r["good"]
        a, u = r.get("author") or {}, r.get("author_usage")
        tokens = (u or {}).get("total") or int(a.get("tokens") or 0)
        rows.append(f"| {r['task']} | {r['verdict']} | {g.get('passes', 0)}/{len(g['runs'])} | "
                    f"{sum(b['caught'] for b in proof)}/{len(proof)} | {sum(b['caught'] for b in held)}/{len(held)} | "
                    f"{len(r['flow_check']['coordinate_fallbacks'])} | {len(r.get('repairs') or [])} | "
                    f"{a.get('model') or a.get('agent') or '-'} | {f'{tokens / 1000:.0f}k' if tokens else '-'} | "
                    f"{r.get('seconds', 0) / 60:.1f} |")
        tot["repairs"] += len(r.get("repairs") or [])
        tot["tokens"] += tokens
        tot["minutes"] += r.get("seconds", 0) / 60
        tot["tasks"] += 1
        tot["proven"] += r["verdict"] == "proven"
        tot["held"] += len(held)
        tot["held_caught"] += sum(b["caught"] for b in held)
        tot["runs"] += len(g["runs"])
        tot["passes"] += g.get("passes", 0)
    flake = 1 - tot["passes"] / tot["runs"] if tot["runs"] else 0
    summary = [f"**{config or 'Results'}:** proof rate {tot['proven']}/{tot['tasks']}, "
               f"held-out bug-catch rate {tot['held_caught']}/{tot['held']}, "
               f"good-build flake rate {flake:.1%} over {tot['runs']} runs, {tot['repairs']} repairs, "
               f"{tot['minutes']:.1f} runner minutes"
               + (f", {tot['tokens'] / 1000:.0f}k author tokens"
                  + (f" ({tot['tokens'] / 1000 / tot['proven']:.0f}k per proven test)" if tot["proven"] else "")
                  if tot["tokens"] else "") + ".", ""]
    return "\n".join(summary + rows) + "\n"
