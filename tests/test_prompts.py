from diagram_scribe.models import Node, Edge, DiagramIR
from diagram_scribe.prompts import (
    build_generate_messages,
    build_refine_messages,
    parse_ir_response,
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
