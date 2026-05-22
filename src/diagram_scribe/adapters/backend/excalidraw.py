"""Excalidraw backend adapter.

Converts a ``DiagramIR`` to Excalidraw JSON and writes it to disk.
On the first ``render()`` call the file is opened in the default browser.
Subsequent calls update the same file in place — the user refreshes the
browser tab to see changes.

Excalidraw file format reference:
https://github.com/excalidraw/excalidraw/blob/master/packages/excalidraw/data/json.ts
"""
from __future__ import annotations
import json
import os
import time
import webbrowser
from ...models import DiagramIR, Node, Edge

_DEFAULT_PATH = os.path.join(os.path.expanduser("~"), ".diagram-scribe", "current.excalidraw")

_SHAPE_MAP = {
    "box": "rectangle",
    "diamond": "diamond",
    "circle": "ellipse",
    "cylinder": "rectangle",
}


def _layout(nodes: list[Node], edges: list[Edge]) -> dict[str, tuple[float, float]]:
    """Assign x/y positions to nodes using a simple topological-level layout.

    Nodes with no incoming edges are placed in the top row (level 0).
    Each subsequent level is 160px below the previous. Nodes at the same
    level are spaced 220px apart horizontally.

    This is intentionally simple — Excalidraw's own auto-layout is richer.
    The goal here is a readable default, not a perfect layout.

    Args:
        nodes: All nodes in the diagram.
        edges: All directed edges.

    Returns:
        Mapping of node id → (x, y) pixel coordinates.
    """
    to_ids = {e.to_id for e in edges}
    starts = [n.id for n in nodes if n.id not in to_ids] or [nodes[0].id]

    levels: dict[str, int] = {}
    queue = [(nid, 0) for nid in starts]
    while queue:
        node_id, level = queue.pop(0)
        if node_id in levels:
            continue
        levels[node_id] = level
        queue.extend((e.to_id, level + 1) for e in edges if e.from_id == node_id)

    counts: dict[int, int] = {}
    positions: dict[str, tuple[float, float]] = {}
    for node in nodes:
        lvl = levels.get(node.id, 0)
        pos = counts.get(lvl, 0)
        counts[lvl] = pos + 1
        positions[node.id] = (pos * 220.0, lvl * 160.0)

    return positions


def _to_excalidraw(ir: DiagramIR) -> dict:
    """Convert a DiagramIR to an Excalidraw file dict.

    The returned dict can be serialised directly to JSON and opened as an
    ``.excalidraw`` file. Every required Excalidraw field is populated;
    optional fields that Excalidraw fills in automatically are omitted or
    set to safe defaults.

    Args:
        ir: The diagram to convert.

    Returns:
        A dict matching the Excalidraw file schema.
    """
    positions = _layout(ir.nodes, ir.edges)
    elements = []
    ts = int(time.time() * 1000)

    for node in ir.nodes:
        x, y = positions.get(node.id, (0.0, 0.0))
        elements.append({
            "id": node.id,
            "type": _SHAPE_MAP.get(node.shape, "rectangle"),
            "x": x, "y": y, "width": 180, "height": 60,
            "angle": 0,
            "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
            "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
            "roughness": 1, "opacity": 100,
            "groupIds": [], "frameId": None,
            "roundness": {"type": 3} if node.shape == "box" else None,
            "seed": abs(hash(node.id)) % 100000,
            "version": 1, "versionNonce": 0, "isDeleted": False,
            "boundElements": [], "updated": ts, "link": None, "locked": False,
            "label": {
                "text": node.label, "fontSize": 14, "fontFamily": 1,
                "textAlign": "center", "verticalAlign": "middle",
            },
        })

    for i, edge in enumerate(ir.edges):
        edge_id = f"edge_{i}"
        elements.append({
            "id": edge_id,
            "type": "arrow",
            "x": 0, "y": 0, "width": 0, "height": 0,
            "angle": 0,
            "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
            "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
            "roughness": 1, "opacity": 100,
            "groupIds": [], "frameId": None, "roundness": {"type": 2},
            "seed": abs(hash(edge_id)) % 100000,
            "version": 1, "versionNonce": 0, "isDeleted": False,
            "boundElements": None, "updated": ts, "link": None, "locked": False,
            "startBinding": {"elementId": edge.from_id, "focus": 0.0, "gap": 8},
            "endBinding": {"elementId": edge.to_id, "focus": 0.0, "gap": 8},
            "lastCommittedPoint": None,
            "startArrowhead": None, "endArrowhead": "arrow",
            "points": [[0, 0], [0, 100]],
            "label": {"text": edge.label} if edge.label else None,
        })

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }


class ExcalidrawAdapter:
    """Backend adapter that renders diagrams as Excalidraw files.

    Writes the diagram to ``~/.diagram-scribe/current.excalidraw`` by
    default (or a custom path if provided). Opens the file in the
    default browser on the first render. Subsequent renders update the
    file in place; the user refreshes the browser tab to see changes.

    Args:
        output_path: Path to write the ``.excalidraw`` file. Defaults to
            ``~/.diagram-scribe/current.excalidraw``.

    Example::

        from diagram_scribe.adapters.backend.excalidraw import ExcalidrawAdapter
        adapter = ExcalidrawAdapter(output_path="/tmp/my-diagram.excalidraw")
        adapter.render(ir)
    """

    def __init__(self, output_path: str | None = None):
        self._output_path = output_path or _DEFAULT_PATH
        self._opened = False

    def render(self, ir: DiagramIR) -> None:
        data = _to_excalidraw(ir)
        os.makedirs(os.path.dirname(self._output_path), exist_ok=True)
        with open(self._output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        if not self._opened:
            webbrowser.open(f"file://{os.path.abspath(self._output_path)}")
            self._opened = True
        else:
            print("Diagram updated — refresh your browser tab to see changes.")
