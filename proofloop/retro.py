"""Retro: group rejected proofs by cause, so a recurring mistake becomes a rule instead of a repeat repair.

"Never write the same review comment twice" (Matt Pocock, AI Engineer 2026). The flow checker's
marker-above-wait rule came from doing this by hand: 6 of 6 authors hid the bug behind a wait. This
reads run records and names each cause with the rule or step that addresses it, so a person can decide
whether a new checker rule is warranted.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

CAUSES = {
    "hidden_by_setup": ("a proof bug failed at setup: a wait or assertion outside the checkpoint saw the broken state first",
                        "covered by the marker-above-wait rule; run proofloop check --fix"),
    "not_observed": ("a proof bug passed: no assertion observes what the bug changes",
                     "plan problem: the checkpoint must assert the state the criterion is about"),
    "wrong_checkpoint": ("a proof bug failed at a different checkpoint than expected",
                         "check the expected checkpoint (the bug's user-visible effect can differ from its code change)"),
    "tripped_on_action": ("a proof bug failed on a tap or input, not an assertion",
                          "assert the state before acting on it, inside the checkpoint"),
    "locator": ("good runs failed finding an element",
                "check learned.md locator fixes (multi-line text needs a trailing .*) and wait timeouts"),
    "broken_setup": ("every good run failed at the same step before any checkpoint",
                     "deterministic, not flaky: the app or device changed under the test (a new screen, overlay or "
                     "onboarding step); repair navigation, re-prove, and read proofloop history for the build it broke on"),
    "flaky": ("good runs failed some of the time", "read the evidence; harness causes are common (see docs/what-failed.md)"),
    "real_bug": ("good runs failed at the same checkpoint every time", "the app may have a real bug: report it"),
    "environment": ("device or Maestro failure", "harness, not the test: proofloop doctor"),
    "policy": ("the flow used a blocked command", "rewrite without it; the allowlist is not negotiable"),
    "approval": ("no approval covers the plan or bugs", "a human approves: proofloop approve"),
    "other": ("other rejection", "read the record"),
}


def cause(r: dict) -> str:
    v, label = r.get("verdict"), r.get("failure_label")
    if v == "rejected_missed_bug":
        for b in r.get("bugs", []):
            if b["role"] == "proof" and not b["caught"]:
                res = b["result"]
                if res["passed"]:
                    return "not_observed"
                return {"setup": "hidden_by_setup", "action": "tripped_on_action"}.get(res["checkpoint"], "wrong_checkpoint")
    if v == "rejected_flaky":
        runs = r.get("good", {}).get("runs", [])
        if runs and all(not x["passed"] and x["checkpoint"] in ("setup", "action") for x in runs) \
                and len({x["step"] for x in runs}) == 1:
            return "broken_setup"
        return {"bad_locator": "locator", "real_bug_in_good_build": "real_bug"}.get(label, "flaky")
    if v == "blocked_environment":
        return "environment"
    if v == "blocked_policy":
        return "policy"
    if v == "needs_human":
        return "approval" if "approv" in (r.get("reason") or "") else "other"
    return "other"


def find_records(paths) -> list[Path]:
    out = []
    for p in map(Path, paths):
        out += [p] if p.is_file() else sorted(list(p.rglob("record.json")) + list(p.rglob("*.record.json")))
    return sorted({f.resolve() for f in out})


def retro(paths) -> str:
    groups: dict[str, list[tuple[Path, dict]]] = defaultdict(list)
    files = find_records(paths)
    proven = 0
    for f in files:
        try:
            r = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if r.get("verdict") == "proven":
            proven += 1
            continue
        groups[cause(r)].append((f, r))
    lines = [f"{len(files)} records: {proven} proven, {sum(map(len, groups.values()))} not proven.", ""]
    for c, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        what, fix = CAUSES[c]
        tag = "RECURRING" if len(items) > 1 else "once"
        lines.append(f"- {len(items)}x {c} ({tag}): {what}. Next: {fix}.")
        for f, r in items[:3]:
            step = next((b["result"]["step"] for b in r.get("bugs", []) if b["role"] == "proof" and not b["caught"]), "") \
                or next((x["step"] for x in r["good"]["runs"] if not x["passed"]), "")
            lines.append(f"    {r['task']}: {re.sub(r'\s+', ' ', r.get('reason', ''))[:110]} [{step}] ({f})")
    return "\n".join(lines) + "\n"
