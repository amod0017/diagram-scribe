from diagram_scribe.models import Node, Edge, DiagramIR, MermaidIR
from diagram_scribe.prompts import (
    build_generate_messages,
    build_refine_messages,
    parse_ir_response,
    parse_response,
    build_mermaid_refine_messages,
)


def test_build_generate_messages_contains_description():
    messages = build_generate_messages("a simple CI/CD flow")
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert "a simple CI/CD flow" in messages[0]["content"]


def test_build_refine_messages_contains_feedback_and_current_ir():
    ir = DiagramIR(nodes=[Node("a", "A", "box")], edges=[])
    messages = build_refine_messages("add a step", ir)
    assert len(messages) == 1
    assert "add a step" in messages[0]["content"]
    assert '"id": "a"' in messages[0]["content"]


def test_parse_ir_response_valid_json():
    text = '{"nodes": [{"id": "a", "label": "Start", "shape": "circle"}], "edges": []}'
    ir = parse_ir_response(text)
    assert len(ir.nodes) == 1
    assert ir.nodes[0].id == "a"
    assert ir.nodes[0].shape == "circle"
    assert ir.edges == []


def test_parse_ir_response_strips_markdown_fences():
    text = '```json\n{"nodes": [{"id": "a", "label": "A", "shape": "box"}], "edges": []}\n```'
    ir = parse_ir_response(text)
    assert len(ir.nodes) == 1


def test_parse_ir_response_with_edges():
    text = (
        '{"nodes": [{"id": "a", "label": "A", "shape": "box"}, '
        '{"id": "b", "label": "B", "shape": "box"}], '
        '"edges": [{"from_id": "a", "to_id": "b", "label": "next"}]}'
    )
    ir = parse_ir_response(text)
    assert len(ir.edges) == 1
    assert ir.edges[0].from_id == "a"
    assert ir.edges[0].label == "next"


def test_parse_ir_response_edge_without_label():
    text = (
        '{"nodes": [{"id": "a", "label": "A", "shape": "box"}, '
        '{"id": "b", "label": "B", "shape": "box"}], '
        '"edges": [{"from_id": "a", "to_id": "b"}]}'
    )
    ir = parse_ir_response(text)
    assert ir.edges[0].label is None


def test_parse_ir_response_strips_think_tags():
    text = (
        "<think>Let me think about this diagram...</think>\n"
        '{"nodes": [{"id": "a", "label": "Start", "shape": "circle"}], "edges": []}'
    )
    ir = parse_ir_response(text)
    assert len(ir.nodes) == 1
    assert ir.nodes[0].id == "a"


def test_parse_ir_response_strips_multiline_think_tags():
    text = (
        "<think>\nReasoning over multiple lines...\nDone.\n</think>\n"
        '```json\n{"nodes": [{"id": "b", "label": "End", "shape": "circle"}], "edges": []}\n```'
    )
    ir = parse_ir_response(text)
    assert ir.nodes[0].id == "b"


def test_parse_response_returns_mermaid_ir_on_mermaid_format():
    text = "FORMAT: mermaid\nflowchart TD\n  A --> B"
    result = parse_response(text)
    assert isinstance(result, MermaidIR)
    assert "flowchart TD" in result.source
    assert "FORMAT: mermaid" not in result.source


def test_parse_response_returns_diagram_ir_on_graph_format():
    text = '{"nodes": [{"id": "a", "label": "A", "shape": "box"}], "edges": []}'
    text_with_header = 'FORMAT: graph\n' + text
    result = parse_response(text_with_header)
    assert isinstance(result, DiagramIR)
    assert result.nodes[0].id == "a"


def test_parse_response_falls_back_to_diagram_ir_when_no_header():
    text = '{"nodes": [{"id": "a", "label": "A", "shape": "box"}], "edges": []}'
    result = parse_response(text)
    assert isinstance(result, DiagramIR)


def test_parse_response_strips_think_tags_before_format_header():
    text = "<think>reasoning</think>\nFORMAT: mermaid\nflowchart TD\n  A --> B"
    result = parse_response(text)
    assert isinstance(result, MermaidIR)


def test_parse_response_detects_diagram_type_from_mermaid_source():
    text = "FORMAT: mermaid\nsequenceDiagram\n  A->>B: hello"
    result = parse_response(text)
    assert isinstance(result, MermaidIR)
    assert result.diagram_type == "sequenceDiagram"


def test_build_mermaid_refine_messages_includes_source_and_feedback():
    ir = MermaidIR(source="flowchart TD\n  A --> B", diagram_type="flowchart")
    messages = build_mermaid_refine_messages("add a C node", ir)
    assert len(messages) == 1
    assert "flowchart TD" in messages[0]["content"]
    assert "add a C node" in messages[0]["content"]
    assert "FORMAT: mermaid" in messages[0]["content"]
