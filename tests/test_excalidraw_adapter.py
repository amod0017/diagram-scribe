import json
from unittest.mock import mock_open, patch
from diagram_scribe.adapters.backend.excalidraw import (
    ExcalidrawAdapter, _to_excalidraw, _node_width, _layout,
)
from diagram_scribe.models import DiagramIR, Node, Edge


def _simple_ir():
    return DiagramIR(
        nodes=[Node("a", "Start", "circle"), Node("b", "End", "circle")],
        edges=[Edge("a", "b")],
    )


# --- structure ---

def test_to_excalidraw_returns_valid_structure():
    data = _to_excalidraw(_simple_ir())
    assert data["type"] == "excalidraw"
    assert data["version"] == 2
    assert "elements" in data


def test_to_excalidraw_has_viewport_state():
    data = _to_excalidraw(_simple_ir())
    state = data["appState"]
    assert "scrollX" in state
    assert "scrollY" in state
    assert "zoom" in state


# --- node shapes ---

def test_to_excalidraw_box_shape():
    ir = DiagramIR(nodes=[Node("n", "Step", "box")], edges=[])
    shapes = [e["type"] for e in _to_excalidraw(ir)["elements"]]
    assert "rectangle" in shapes


def test_to_excalidraw_diamond_shape():
    ir = DiagramIR(nodes=[Node("n", "Decision", "diamond")], edges=[])
    shapes = [e["type"] for e in _to_excalidraw(ir)["elements"]]
    assert "diamond" in shapes


def test_to_excalidraw_circle_shape():
    ir = DiagramIR(nodes=[Node("n", "Start", "circle")], edges=[])
    shapes = [e["type"] for e in _to_excalidraw(ir)["elements"]]
    assert "ellipse" in shapes


# --- labels as separate text elements ---

def test_node_has_separate_text_element():
    ir = DiagramIR(nodes=[Node("x", "My Label", "box")], edges=[])
    elements = _to_excalidraw(ir)["elements"]
    text_el = next((e for e in elements if e.get("containerId") == "x"), None)
    assert text_el is not None
    assert text_el["type"] == "text"
    assert text_el["text"] == "My Label"


def test_node_shape_has_bound_text_element():
    ir = DiagramIR(nodes=[Node("x", "My Label", "box")], edges=[])
    elements = _to_excalidraw(ir)["elements"]
    shape = next(e for e in elements if e["id"] == "x")
    bound = shape.get("boundElements", [])
    assert any(b["type"] == "text" for b in bound)


def test_all_nodes_have_text_elements():
    ir = _simple_ir()
    elements = _to_excalidraw(ir)["elements"]
    text_elements = [e for e in elements if e.get("type") == "text" and e.get("containerId")]
    assert len(text_elements) == len(ir.nodes)


# --- dynamic node width ---

def test_node_width_minimum_is_180():
    assert _node_width("Hi") >= 180


def test_node_width_grows_with_label_length():
    short = _node_width("A")
    long = _node_width("Token for Other Microservices")
    assert long > short


def test_long_label_node_has_wider_element():
    short_ir = DiagramIR(nodes=[Node("s", "A", "box")], edges=[])
    long_ir = DiagramIR(nodes=[Node("l", "Token for Other Microservices", "box")], edges=[])

    short_w = next(e["width"] for e in _to_excalidraw(short_ir)["elements"] if e["id"] == "s")
    long_w = next(e["width"] for e in _to_excalidraw(long_ir)["elements"] if e["id"] == "l")
    assert long_w > short_w


# --- arrows ---

def test_arrow_connects_correct_nodes():
    data = _to_excalidraw(_simple_ir())
    arrow = next(e for e in data["elements"] if e["type"] == "arrow")
    assert arrow["startBinding"]["elementId"] == "a"
    assert arrow["endBinding"]["elementId"] == "b"


def test_arrow_starts_at_source_bottom_center():
    ir = DiagramIR(
        nodes=[Node("a", "A", "box"), Node("b", "B", "box")],
        edges=[Edge("a", "b")],
    )
    elements = _to_excalidraw(ir)["elements"]
    arrow = next(e for e in elements if e["type"] == "arrow")
    node_a = next(e for e in elements if e["id"] == "a")
    expected_x = node_a["x"] + node_a["width"] / 2
    expected_y = node_a["y"] + node_a["height"]
    assert arrow["x"] == expected_x
    assert arrow["y"] == expected_y


def test_arrow_points_end_at_destination():
    ir = DiagramIR(
        nodes=[Node("a", "A", "box"), Node("b", "B", "box")],
        edges=[Edge("a", "b")],
    )
    elements = _to_excalidraw(ir)["elements"]
    arrow = next(e for e in elements if e["type"] == "arrow")
    points = arrow["points"]
    assert points[0] == [0, 0]
    # end point should reach destination top center
    assert points[-1][1] > 0  # arrow goes downward


# --- edge labels ---

def test_edge_with_label_creates_text_element():
    ir = DiagramIR(
        nodes=[Node("a", "A", "box"), Node("b", "B", "box")],
        edges=[Edge("a", "b", label="yes")],
    )
    elements = _to_excalidraw(ir)["elements"]
    label_texts = [
        e["text"] for e in elements
        if e.get("type") == "text" and e.get("containerId") is None
    ]
    assert "yes" in label_texts


def test_edge_without_label_creates_no_extra_text():
    ir = DiagramIR(
        nodes=[Node("a", "A", "box"), Node("b", "B", "box")],
        edges=[Edge("a", "b")],
    )
    elements = _to_excalidraw(ir)["elements"]
    # only node text elements (with containerId), no floating label text
    floating_texts = [
        e for e in elements
        if e.get("type") == "text" and e.get("containerId") is None
    ]
    assert len(floating_texts) == 0


# --- layout ---

def test_layout_root_nodes_at_level_zero():
    nodes = [Node("a", "A", "box"), Node("b", "B", "box")]
    edges = [Edge("a", "b")]
    positions = _layout(nodes, edges)
    assert positions["a"][1] == 0.0


def test_layout_child_nodes_below_parent():
    nodes = [Node("a", "A", "box"), Node("b", "B", "box")]
    edges = [Edge("a", "b")]
    positions = _layout(nodes, edges)
    assert positions["b"][1] > positions["a"][1]


# --- render ---

def test_render_opens_browser_on_first_call():
    ir = _simple_ir()
    with patch("diagram_scribe.adapters.backend.excalidraw.webbrowser.open") as mock_browser, \
         patch("builtins.open", mock_open()), \
         patch("diagram_scribe.adapters.backend.excalidraw.os.makedirs"):
        ExcalidrawAdapter().render(ir)
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
        ExcalidrawAdapter(output_path="/custom/path.excalidraw").render(ir)
        mock_file.assert_called_with("/custom/path.excalidraw", "w", encoding="utf-8")
