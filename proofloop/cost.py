"""Authoring cost: tokens an agent session spent, read from Claude Code's local transcripts.

The runner makes no model calls; the test author does. When task.json names the author's session
(`"author": {"session": "<session id or subagent id>"}`), prove sums that session's usage from
~/.claude/projects/*/<id>.jsonl (or a subagent's agent-<id>.jsonl) into the record.

ponytail: one transcript format (Claude Code's). Other agents report usage by hand in task.json
("author": {"tokens": N}).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path.home() / ".claude" / "projects"


def find_transcript(session: str, root: Path = ROOT) -> Path | None:
    sid = session.removeprefix("agent-")
    for pattern in (f"*/{sid}.jsonl", f"*/*/subagents/agent-{sid}.jsonl"):
        hits = sorted(root.glob(pattern))
        if hits:
            return hits[0]
    return None


def session_usage(session: str, root: Path = ROOT) -> dict | None:
    path = find_transcript(session, root)
    if path is None:
        return None
    per_request: dict[str, dict] = {}  # streamed responses repeat a request's usage; keep the last
    models = set()
    for n, line in enumerate(path.read_text().splitlines()):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        m = d.get("message")
        if not isinstance(m, dict) or not isinstance(m.get("usage"), dict):
            continue
        per_request[d.get("requestId") or m.get("id") or str(n)] = m["usage"]
        if m.get("model"):
            models.add(m["model"])
    if not per_request:
        return None
    total = {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0}
    for u in per_request.values():
        total["input"] += u.get("input_tokens", 0) or 0
        total["cache_write"] += u.get("cache_creation_input_tokens", 0) or 0
        total["cache_read"] += u.get("cache_read_input_tokens", 0) or 0
        total["output"] += u.get("output_tokens", 0) or 0
    total["total"] = sum(total.values())  # tokens processed across all requests (cache reads re-count context)
    # largest single request: the context the session reached, the figure Claude Code reports per subagent
    total["peak_context"] = max((u.get("input_tokens", 0) or 0) + (u.get("cache_creation_input_tokens", 0) or 0)
                                + (u.get("cache_read_input_tokens", 0) or 0) + (u.get("output_tokens", 0) or 0)
                                for u in per_request.values())
    total["requests"] = len(per_request)
    total["models"] = sorted(models)
    total["transcript"] = str(path)
    return total
