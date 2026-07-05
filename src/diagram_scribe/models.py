from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Node:
    """A single node in a diagram.

    Attributes:
        id: Unique identifier used to reference this node in edges.
        label: Display text rendered inside the shape.
        shape: Visual shape. One of ``"box"``, ``"diamond"``, ``"circle"``,
            ``"cylinder"``, or ``"text"`` (floating label, no border).
    """
    id: str
    label: str
    shape: str


@dataclass
class Edge:
    """A directed connection between two nodes.

    Attributes:
        from_id: ``id`` of the source node.
        to_id: ``id`` of the target node.
        label: Optional text rendered along the arrow.
    """
    from_id: str
    to_id: str
    label: str | None = None


@dataclass
class DiagramIR:
    """Intermediate representation of a diagram.

    This is the contract between LLM adapters and backend adapters.
    LLM adapters produce a ``DiagramIR``; backend adapters consume one.
    Neither side needs to know anything about the other.

    Attributes:
        nodes: All nodes in the diagram, in no particular order.
        edges: All directed edges, referencing nodes by ``id``.
    """
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)


@dataclass
class MermaidIR:
    """Intermediate representation for Mermaid-rendered diagrams.

    Attributes:
        source: Raw Mermaid diagram text (e.g. ``flowchart TD\\n  A --> B``).
        diagram_type: Mermaid diagram keyword (flowchart, sequenceDiagram, etc.).
            Used for logging and debugging.
    """
    source: str
    diagram_type: str = "flowchart"
