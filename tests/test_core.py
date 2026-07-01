import pytest
from unittest.mock import MagicMock
from diagram_scribe.core import DiagramScribe
from diagram_scribe.models import DiagramIR, Node, MermaidIR


def _make_ir(*labels: str) -> DiagramIR:
    return DiagramIR(nodes=[Node(f"n{i}", label, "box") for i, label in enumerate(labels)], edges=[])


def test_draw_calls_llm_generate():
    mock_llm = MagicMock()
    mock_llm.generate.return_value = _make_ir("A")
    mock_backend = MagicMock()

    ds = DiagramScribe(llm=mock_llm, backend=mock_backend)
    ds.draw("a CI/CD flow")

    mock_llm.generate.assert_called_once_with("a CI/CD flow")


def test_draw_calls_backend_render():
    mock_llm = MagicMock()
    ir = _make_ir("A")
    mock_llm.generate.return_value = ir
    mock_backend = MagicMock()

    ds = DiagramScribe(llm=mock_llm, backend=mock_backend)
    ds.draw("a flow")

    mock_backend.render.assert_called_once_with(ir)


def test_refine_calls_llm_refine_with_current_ir():
    initial_ir = _make_ir("A")
    refined_ir = _make_ir("A", "B")

    mock_llm = MagicMock()
    mock_llm.generate.return_value = initial_ir
    mock_llm.refine.return_value = refined_ir
    mock_backend = MagicMock()

    ds = DiagramScribe(llm=mock_llm, backend=mock_backend)
    ds.draw("a flow")
    ds.refine("add a step")

    mock_llm.refine.assert_called_once_with("add a step", initial_ir)


def test_refine_renders_updated_ir():
    initial_ir = _make_ir("A")
    refined_ir = _make_ir("A", "B")

    mock_llm = MagicMock()
    mock_llm.generate.return_value = initial_ir
    mock_llm.refine.return_value = refined_ir
    mock_backend = MagicMock()

    ds = DiagramScribe(llm=mock_llm, backend=mock_backend)
    ds.draw("a flow")
    ds.refine("add a step")

    assert mock_backend.render.call_count == 2
    mock_backend.render.assert_called_with(refined_ir)


def test_refine_before_draw_raises_runtime_error():
    ds = DiagramScribe(llm=MagicMock(), backend=MagicMock())

    with pytest.raises(RuntimeError, match=r"Call draw\(\) before refine\(\)"):
        ds.refine("add a step")


def test_multiple_refines_chain_correctly():
    ir1 = _make_ir("A")
    ir2 = _make_ir("A", "B")
    ir3 = _make_ir("A", "B", "C")

    mock_llm = MagicMock()
    mock_llm.generate.return_value = ir1
    mock_llm.refine.side_effect = [ir2, ir3]
    mock_backend = MagicMock()

    ds = DiagramScribe(llm=mock_llm, backend=mock_backend)
    ds.draw("a flow")
    ds.refine("add B")
    ds.refine("add C")

    calls = mock_llm.refine.call_args_list
    assert calls[0].args == ("add B", ir1)
    assert calls[1].args == ("add C", ir2)


def test_draw_routes_mermaid_ir_to_mermaid_adapter():
    mermaid_ir = MermaidIR(source="flowchart TD\n  A --> B", diagram_type="flowchart")
    mock_llm = MagicMock()
    mock_llm.generate.return_value = mermaid_ir
    mock_mermaid_backend = MagicMock()

    ds = DiagramScribe(llm=mock_llm, backend=MagicMock())
    ds._mermaid_backend = mock_mermaid_backend

    result = ds.draw("login flow")
    mock_mermaid_backend.render.assert_called_once_with(mermaid_ir)
    assert isinstance(result, MermaidIR)


def test_draw_routes_diagram_ir_to_excalidraw_backend():
    diagram_ir = DiagramIR(nodes=[Node("a", "A", "box")], edges=[])
    mock_llm = MagicMock()
    mock_llm.generate.return_value = diagram_ir
    mock_backend = MagicMock()

    ds = DiagramScribe(llm=mock_llm, backend=mock_backend)
    result = ds.draw("simple flow")
    mock_backend.render.assert_called_once_with(diagram_ir)
    assert isinstance(result, DiagramIR)


def test_refine_routes_mermaid_ir_correctly():
    initial_ir = MermaidIR(source="flowchart TD\n  A --> B", diagram_type="flowchart")
    refined_ir = MermaidIR(source="flowchart TD\n  A --> B --> C", diagram_type="flowchart")
    mock_llm = MagicMock()
    mock_llm.generate.return_value = initial_ir
    mock_llm.refine.return_value = refined_ir
    mock_mermaid_backend = MagicMock()

    ds = DiagramScribe(llm=mock_llm, backend=MagicMock())
    ds._mermaid_backend = mock_mermaid_backend
    ds.draw("flow")
    result = ds.refine("add C")

    assert mock_mermaid_backend.render.call_count == 2
    assert isinstance(result, MermaidIR)


def test_diagram_scribe_accepts_output_path():
    ds = DiagramScribe(llm=MagicMock(), backend=MagicMock(), output_path="/tmp/test.excalidraw")
    assert ds._output_path == "/tmp/test.excalidraw"
