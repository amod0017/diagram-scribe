import json
import os
import pytest
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
