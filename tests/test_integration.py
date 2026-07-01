import json
import os
import shutil
import pytest
from unittest.mock import patch, MagicMock
from diagram_scribe import DiagramScribe
from diagram_scribe.adapters.backend.excalidraw import ExcalidrawAdapter


@pytest.mark.integration
def test_claude_generates_valid_excalidraw(tmp_path):
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    output = tmp_path / "diagram.excalidraw"
    ds = DiagramScribe(backend=ExcalidrawAdapter(output_path=str(output)))
    ds.draw("Two steps: user logs in, then sees the dashboard")

    assert output.exists(), "ExcalidrawAdapter did not write file"
    data = json.loads(output.read_text())
    assert data["type"] == "excalidraw"
    assert len(data["elements"]) >= 2, "Expected at least 2 elements"


@pytest.mark.integration
def test_claude_refine_updates_diagram(tmp_path):
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    output = tmp_path / "diagram.excalidraw"
    ds = DiagramScribe(backend=ExcalidrawAdapter(output_path=str(output)))
    ds.draw("Two steps: user logs in, then sees the dashboard")

    before = json.loads(output.read_text())
    before_count = len(before["elements"])

    ds.refine("add a password reset step after login")

    after = json.loads(output.read_text())
    after_count = len(after["elements"])

    assert after_count >= before_count, "refine() should not reduce the diagram"


@pytest.mark.integration
def test_openrouter_generates_valid_excalidraw(tmp_path):
    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY not set")

    from diagram_scribe.adapters.llm.openrouter import OpenRouterAdapter

    output = tmp_path / "diagram.excalidraw"
    ds = DiagramScribe(
        llm=OpenRouterAdapter(
            api_key=os.environ["OPENROUTER_API_KEY"],
            model=os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free"),
        ),
        backend=ExcalidrawAdapter(output_path=str(output)),
    )
    ds.draw("CI/CD pipeline — push code, run tests, deploy to staging")

    assert output.exists()
    data = json.loads(output.read_text())
    assert data["type"] == "excalidraw"
    assert len(data["elements"]) >= 2


@pytest.mark.integration
def test_mermaid_path_writes_valid_excalidraw(tmp_path):
    """Full Mermaid path: MermaidIR → real Node.js bundle → .excalidraw file."""
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    from diagram_scribe.models import MermaidIR
    from diagram_scribe.adapters.backend.mermaid import MermaidAdapter

    output = tmp_path / "mermaid.excalidraw"
    adapter = MermaidAdapter(output_path=str(output))

    ir = MermaidIR(source="flowchart TD\n  A[Start] --> B[End]", diagram_type="flowchart")
    with patch("diagram_scribe.adapters.backend.mermaid.webbrowser.open"):
        adapter.render(ir)

    assert output.exists(), "MermaidAdapter did not write file"
    data = json.loads(output.read_text())
    assert data["type"] == "excalidraw"
    assert len(data["elements"]) >= 1, "Expected at least 1 element from Mermaid conversion"


@pytest.mark.integration
def test_diagram_scribe_routes_mermaid_ir_end_to_end(tmp_path):
    """DiagramScribe routes MermaidIR to MermaidAdapter through the real Node.js bundle."""
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    from diagram_scribe.models import MermaidIR

    output = tmp_path / "mermaid.excalidraw"
    mermaid_ir = MermaidIR(source="flowchart TD\n  A[Start] --> B[End]", diagram_type="flowchart")

    mock_llm = MagicMock()
    mock_llm.generate.return_value = mermaid_ir

    ds = DiagramScribe(llm=mock_llm, output_path=str(output))
    with patch("diagram_scribe.adapters.backend.mermaid.webbrowser.open"):
        ds.draw("a simple flowchart")

    assert output.exists(), "DiagramScribe did not write .excalidraw file for MermaidIR"
    data = json.loads(output.read_text())
    assert data["type"] == "excalidraw"
    assert len(data["elements"]) >= 1


@pytest.mark.integration
def test_ollama_generates_valid_excalidraw(tmp_path):
    if not os.getenv("OLLAMA_MODEL"):
        pytest.skip("OLLAMA_MODEL not set")

    from diagram_scribe.adapters.llm.ollama import OllamaAdapter

    output = tmp_path / "diagram.excalidraw"
    ds = DiagramScribe(
        llm=OllamaAdapter(model=os.environ["OLLAMA_MODEL"]),
        backend=ExcalidrawAdapter(output_path=str(output)),
    )
    ds.draw("CI/CD pipeline — push code, run tests, deploy to staging")

    assert output.exists()
    data = json.loads(output.read_text())
    assert data["type"] == "excalidraw"
    assert len(data["elements"]) >= 2
