"""App map: screens, the actions between them, notes per screen, and known routes.

Memory for the authoring agent (idea from askui's agent-memory talk, nextapp devCon 2026):
read before exploring so the agent does not rediscover the app every time.
Plain markdown with a small line grammar, so people and agents can both edit it:

    # App map: Sunflower
    app: com.google.samples.apps.sunflower

    ## screen: garden
    anchors: "My garden", "Plant list"
    - tap "Plant list" -> plant_list
    - tap "Upgrade" -> ? (not taken: purchase)
    - back -> exit
    - rule: the list shows only planted plants
    - hazard: long-press deletes without asking

    ## route: plant-a-plant
    1. garden: tap "Plant list"
    2. plant_list: tap "Avocado"

Note kinds: precondition, rule, lookup, hazard. A target of "?" marks an action that was seen
but not taken; "exit" leaves the app.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

NOTE_KINDS = ("precondition", "rule", "lookup", "hazard")
ACTIONS = ("tap", "longpress", "input", "scroll", "back", "swipe")

_HEAD = re.compile(r"^##\s+(screen|route):\s*([\w-]+)\s*$")
_EDGE = re.compile(r'^-\s+(\w+)(?:\s+"([^"]+)")?\s*->\s*([\w-]+|\?)\s*(?:\((.*)\))?\s*$')
_NOTE = re.compile(r"^-\s+(\w+):\s*(.+)$")
_STEP = re.compile(r"^\d+\.\s+([\w-]+):")
_QUOTED = re.compile(r'"([^"]+)"')


@dataclass
class Edge:
    action: str
    locator: str
    target: str
    reason: str = ""


@dataclass
class Screen:
    id: str
    anchors: list[str] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    notes: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class AppMap:
    app: str = ""
    screens: dict[str, Screen] = field(default_factory=dict)
    routes: dict[str, list[str]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def parse(text: str) -> AppMap:
    m = AppMap()
    cur = None  # ("screen", Screen) or ("route", name)
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("# ") or line.startswith(">"):
            continue
        if line.startswith("app:"):
            m.app = line[4:].strip()
            continue
        h = _HEAD.match(line)
        if h:
            kind, name = h.groups()
            if kind == "screen":
                if name in m.screens:
                    m.errors.append(f"line {n}: screen '{name}' defined twice")
                cur = ("screen", m.screens.setdefault(name, Screen(name)))
            else:
                cur = ("route", name)
                m.routes[name] = []
            continue
        if cur is None:
            continue
        if cur[0] == "route":
            if _STEP.match(line):
                m.routes[cur[1]].append(line)
            continue
        s = cur[1]
        if line.startswith("anchors:"):
            s.anchors += _QUOTED.findall(line)
            continue
        e = _EDGE.match(line)
        if e:
            action, loc, target, reason = e.groups()
            if action not in ACTIONS:
                m.errors.append(f"line {n}: unknown action '{action}' (use {', '.join(ACTIONS)})")
            s.edges.append(Edge(action, loc or "", target, reason or ""))
            continue
        k = _NOTE.match(line)
        if k:
            if k.group(1) not in NOTE_KINDS:
                m.errors.append(f"line {n}: unknown note kind '{k.group(1)}' (use {', '.join(NOTE_KINDS)})")
            s.notes.append((k.group(1), k.group(2)))
            continue
        if line.startswith("-"):
            m.errors.append(f"line {n}: not an edge or note: {line}")
    return m


def check(m: AppMap) -> list[str]:
    errs = list(m.errors)
    if not m.app:
        errs.append("missing 'app:' line")
    if not m.screens:
        errs.append("no screens")
    for s in m.screens.values():
        if not s.anchors:
            errs.append(f"screen '{s.id}' has no anchors (text that is always on it)")
        for e in s.edges:
            if e.target not in ("?", "exit") and e.target not in m.screens:
                errs.append(f"screen '{s.id}': edge to unknown screen '{e.target}'")
            if e.action not in ("back",) and not e.locator:
                errs.append(f"screen '{s.id}': '{e.action}' edge needs a quoted locator")
    for name, steps in m.routes.items():
        if not steps:
            errs.append(f"route '{name}' has no steps")
        for st in steps:
            sid = _STEP.match(st).group(1)
            if sid not in m.screens:
                errs.append(f"route '{name}': unknown screen '{sid}'")
    return errs


def ambiguous_anchors(m: AppMap) -> dict[tuple[str, str], list[str]]:
    """Anchors that are also visible on another screen: another screen lists them as an anchor, or
    taps them (a tab label). Seeing such text does not identify the screen. {(screen, anchor): others}"""
    out = {}
    for s in m.screens.values():
        for a in s.anchors:
            others = [t.id for t in m.screens.values() if t is not s
                      and (a in t.anchors or any(e.locator == a for e in t.edges))]
            if others:
                out[(s.id, a)] = others
    return out


def unreachable(m: AppMap) -> list[str]:
    """Screens no edge leads to from the first screen (the launch screen)."""
    if not m.screens:
        return []
    start = next(iter(m.screens))
    seen, todo = {start}, [start]
    while todo:
        for e in m.screens[todo.pop()].edges:
            if e.target in m.screens and e.target not in seen:
                seen.add(e.target)
                todo.append(e.target)
    return [s for s in m.screens if s not in seen]


def coverage(m: AppMap, flow_texts: list[str]) -> dict:
    """Which screens and actions the given Maestro flows touch.

    ponytail: text matching, not execution. A screen counts as visited when a flow quotes one of
    its anchors; an action counts when a flow taps or types into its locator. Upgrade path: map
    each flow command to a screen from run evidence (hierarchy per step).
    """
    quoted = set()
    tapped = set()
    for t in flow_texts:
        for line in t.splitlines():
            q = _QUOTED.findall(line)
            quoted.update(q)
            if re.match(r"\s*-\s*(tapOn|longPressOn|inputText)\b", line):
                tapped.update(q)
    screens = {s.id: any(a in quoted for a in s.anchors) for s in m.screens.values()}
    edges = {f"{s.id}: {e.action} \"{e.locator}\" -> {e.target}": e.locator in tapped
             for s in m.screens.values() for e in s.edges if e.locator and e.target != "?"}
    return {"screens": screens, "edges": edges}


def load(path) -> AppMap:
    return parse(Path(path).read_text())
