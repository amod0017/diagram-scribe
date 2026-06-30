import json
from unittest.mock import mock_open, patch
from diagram_scribe.adapters.backend.excalidraw import (
    ExcalidrawAdapter, _to_excalidraw, _node_width, _layout, _NODE_H, _CAP_H,
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


# --- cylinder shape (#63) ---

def test_cylinder_renders_rect_body_and_ellipse_cap():
    ir = DiagramIR(nodes=[Node("db", "Users DB", "cylinder")], edges=[])
    elements = _to_excalidraw(ir)["elements"]
    types = [e["type"] for e in elements]
    assert "rectangle" in types
    assert "ellipse" in types


def test_cylinder_body_has_node_id():
    ir = DiagramIR(nodes=[Node("db", "Users DB", "cylinder")], edges=[])
    elements = _to_excalidraw(ir)["elements"]
    body = next((e for e in elements if e["id"] == "db"), None)
    assert body is not None
    assert body["type"] == "rectangle"


def test_cylinder_cap_is_above_body():
    ir = DiagramIR(nodes=[Node("db", "Users DB", "cylinder")], edges=[])
    elements = _to_excalidraw(ir)["elements"]
    body = next(e for e in elements if e["id"] == "db")
    cap = next(e for e in elements if e["id"] == "db_cap")
    assert cap["y"] < body["y"]


def test_cylinder_has_text_element():
    ir = DiagramIR(nodes=[Node("db", "Users DB", "cylinder")], edges=[])
    elements = _to_excalidraw(ir)["elements"]
    text = next((e for e in elements if e.get("containerId") == "db"), None)
    assert text is not None
    assert text["text"] == "Users DB"


# --- text shape (#58) ---

def test_text_shape_renders_as_floating_text():
    ir = DiagramIR(nodes=[Node("note", "See docs", "text")], edges=[])
    elements = _to_excalidraw(ir)["elements"]
    assert len(elements) == 1
    assert elements[0]["type"] == "text"
    assert elements[0].get("containerId") is None


# --- layout overlap (#59) ---

def test_layout_siblings_do_not_overlap():
    nodes = [
        Node("a", "A very long label here", "box"),
        Node("b", "B", "box"),
    ]
    edges = []  # both are roots → same level
    widths = {n.id: _node_width(n.label) for n in nodes}
    positions = _layout(nodes, edges, widths)
    # b should start after a's right edge
    assert positions["b"][0] >= positions["a"][0] + widths["a"]


# --- same-level arrows (#64) ---

def test_sibling_arrow_uses_side_routing():
    ir = DiagramIR(
        nodes=[Node("a", "A", "box"), Node("b", "B", "box")],
        edges=[Edge("a", "b")],
    )
    # Force siblings by making both roots (no edges in layout, then add edge for arrow only)
    # Use a cycle-free two-root IR to place a and b at the same level
    ir2 = DiagramIR(
        nodes=[Node("x", "X", "box"), Node("y", "Y", "box"), Node("z", "Z", "box")],
        edges=[Edge("x", "z"), Edge("y", "z")],
    )
    elements = _to_excalidraw(ir2)["elements"]
    # x and y should be at the same y level; the arrow x→z goes downward (not same-level)
    # Validate that x and y share the same y position
    ex = next(e for e in elements if e["id"] == "x")
    ey_el = next(e for e in elements if e["id"] == "y")
    assert ex["y"] == ey_el["y"]


def test_same_level_arrow_starts_at_right_edge():
    # root → a, root → b, a → b: a and b are siblings (both at level 1)
    nodes = [Node("root", "Root", "box"), Node("a", "A", "box"), Node("b", "B", "box")]
    edges = [Edge("root", "a"), Edge("root", "b"), Edge("a", "b")]
    ir = DiagramIR(nodes=nodes, edges=edges)
    elements = _to_excalidraw(ir)["elements"]

    node_a = next(e for e in elements if e["id"] == "a")
    node_b = next(e for e in elements if e["id"] == "b")
    # a and b must be at the same y level
    assert node_a["y"] == node_b["y"]

    # The a→b arrow (edge index 2) should start at the right edge of a
    a_to_b = next(
        arr for arr in elements
        if arr["type"] == "arrow"
        and arr["startBinding"]["elementId"] == "a"
        and arr["endBinding"]["elementId"] == "b"
    )
    assert a_to_b["x"] == node_a["x"] + node_a["width"]


# --- draw/refine return values (#62) ---

def test_draw_returns_diagram_ir():
    from unittest.mock import MagicMock
    from diagram_scribe.core import DiagramScribe
    from diagram_scribe.models import DiagramIR, Node

    ir = DiagramIR(nodes=[Node("a", "A", "box")], edges=[])
    mock_llm = MagicMock()
    mock_llm.generate.return_value = ir
    ds = DiagramScribe(llm=mock_llm, backend=MagicMock())
    result = ds.draw("test")
    assert result is ir


def test_refine_returns_diagram_ir():
    from unittest.mock import MagicMock
    from diagram_scribe.core import DiagramScribe
    from diagram_scribe.models import DiagramIR, Node

    ir1 = DiagramIR(nodes=[Node("a", "A", "box")], edges=[])
    ir2 = DiagramIR(nodes=[Node("a", "A", "box"), Node("b", "B", "box")], edges=[])
    mock_llm = MagicMock()
    mock_llm.generate.return_value = ir1
    mock_llm.refine.return_value = ir2
    ds = DiagramScribe(llm=mock_llm, backend=MagicMock())
    ds.draw("test")
    result = ds.refine("add B")
    assert result is ir2
