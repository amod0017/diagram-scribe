from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Node:
    id: str
    label: str
    shape: str  # "box", "diamond", "circle", "cylinder"


@dataclass
class Edge:
    from_id: str
    to_id: str
    label: str | None = None


@dataclass
class DiagramIR:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
