import json
from unittest.mock import mock_open, patch
from diagram_scribe.adapters.backend.excalidraw import ExcalidrawAdapter, _to_excalidraw
from diagram_scribe.models import DiagramIR, Node, Edge


def _simple_ir():
    return DiagramIR(
        nodes=[Node("a", "Start", "circle"), Node("b", "End", "circle")],
        edges=[Edge("a", "b")],
    )


def test_to_excalidraw_returns_valid_structure():
    ir = _simple_ir()
    data = _to_excalidraw(ir)
    assert data["type"] == "excalidraw"
    assert data["version"] == 2
    assert "elements" in data


def test_to_excalidraw_includes_all_nodes():
    ir = _simple_ir()
    data = _to_excalidraw(ir)
    node_ids = {e["id"] for e in data["elements"] if e["type"] != "arrow"}
    assert "a" in node_ids
    assert "b" in node_ids


def test_to_excalidraw_includes_edge_as_arrow():
    ir = _simple_ir()
    data = _to_excalidraw(ir)
    arrows = [e for e in data["elements"] if e["type"] == "arrow"]
    assert len(arrows) == 1
    assert arrows[0]["startBinding"]["elementId"] == "a"
    assert arrows[0]["endBinding"]["elementId"] == "b"


def test_to_excalidraw_diamond_shape():
    ir = DiagramIR(nodes=[Node("d", "Decision", "diamond")], edges=[])
    data = _to_excalidraw(ir)
    element = data["elements"][0]
    assert element["type"] == "diamond"


def test_to_excalidraw_circle_shape():
    ir = DiagramIR(nodes=[Node("c", "Start", "circle")], edges=[])
    data = _to_excalidraw(ir)
    assert data["elements"][0]["type"] == "ellipse"


def test_to_excalidraw_box_shape():
    ir = DiagramIR(nodes=[Node("b", "Step", "box")], edges=[])
    data = _to_excalidraw(ir)
    assert data["elements"][0]["type"] == "rectangle"


def test_to_excalidraw_edge_with_label():
    ir = DiagramIR(
        nodes=[Node("a", "A", "box"), Node("b", "B", "box")],
        edges=[Edge("a", "b", label="yes")],
    )
    data = _to_excalidraw(ir)
    arrow = next(e for e in data["elements"] if e["type"] == "arrow")
    assert arrow["label"]["text"] == "yes"


def test_to_excalidraw_edge_without_label():
    ir = DiagramIR(
        nodes=[Node("a", "A", "box"), Node("b", "B", "box")],
        edges=[Edge("a", "b")],
    )
    data = _to_excalidraw(ir)
    arrow = next(e for e in data["elements"] if e["type"] == "arrow")
    assert arrow["label"] is None


def test_render_opens_browser_on_first_call():
    ir = _simple_ir()
    with patch("diagram_scribe.adapters.backend.excalidraw.webbrowser.open") as mock_browser, \
         patch("builtins.open", mock_open()), \
         patch("diagram_scribe.adapters.backend.excalidraw.os.makedirs"):
        adapter = ExcalidrawAdapter()
        adapter.render(ir)
        mock_browser.assert_called_once()


def test_render_does_not_open_browser_on_subsequent_calls():
    ir = _simple_ir()
    with patch("diagram_scribe.adapters.backend.excalidraw.webbrowser.open") as mock_browser, \
         patch("builtins.open", mock_open()), \
         patch("diagram_scribe.adapters.backend.excalidraw.os.makedirs"):
        adapter = ExcalidrawAdapter()
        adapter.render(ir)
        adapter.render(ir)
        assert mock_browser.call_count == 1


def test_render_uses_output_path_when_provided():
    ir = _simple_ir()
    with patch("diagram_scribe.adapters.backend.excalidraw.webbrowser.open"), \
         patch("builtins.open", mock_open()) as mock_file, \
         patch("diagram_scribe.adapters.backend.excalidraw.os.makedirs"):
        adapter = ExcalidrawAdapter(output_path="/custom/path.excalidraw")
        adapter.render(ir)
        mock_file.assert_called_with("/custom/path.excalidraw", "w", encoding="utf-8")
