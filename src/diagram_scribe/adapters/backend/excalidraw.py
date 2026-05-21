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
    # nodes with no incoming edges start at level 0
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
