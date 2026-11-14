"""Failure label: one label per completed run record, so repeated failures can be grouped.

ponytail: rules over the record, no model call. Add a small model only if evals show
these rules mislabel runs often enough to matter.
"""

LABELS = ("none", "environment", "policy_block", "bad_locator", "flaky", "missed_bug", "real_bug_in_good_build",
          "needs_human", "budget")


def label_record(record: dict) -> str:
    verdict = record.get("verdict")
    if verdict == "proven":
        return "none"
    if verdict == "blocked_environment":
        return "environment"
    if verdict == "blocked_policy":
        return "policy_block"
    if verdict == "needs_human":
        return "needs_human"
    if verdict == "budget_exhausted":
        return "budget"
    runs = record.get("good", {}).get("runs", [])
    failed = [r for r in runs if not r["passed"]]
    if verdict == "rejected_flaky" and failed:
        if all(r["checkpoint"] in ("setup", "action") and "not found" in r["error"].lower() for r in failed) \
                and len(failed) == len(runs):
            return "bad_locator"
        if len(failed) == len(runs) and all(r["checkpoint"] not in ("setup", "action") for r in failed) \
                and len({r["checkpoint"] for r in failed}) == 1:
            return "real_bug_in_good_build"  # same checkpoint fails every time on the good build
        return "flaky"
    if verdict == "rejected_missed_bug":
        return "missed_bug"
    return "needs_human"
