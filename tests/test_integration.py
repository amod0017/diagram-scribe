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
def test_example_prompt_flowchart_login(tmp_path):
    """README example: login flow flowchart with decision branches."""
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    from diagram_scribe.models import MermaidIR

    output = tmp_path / "login_flowchart.excalidraw"
    ir = MermaidIR(
        source=(
            "flowchart TD\n"
            "  A[User submits login form] --> B{System validates credentials}\n"
            "  B -->|Valid| C[Show dashboard]\n"
            "  B -->|Invalid| D[Show error message]"
        ),
        diagram_type="flowchart",
    )
    mock_llm = MagicMock()
    mock_llm.generate.return_value = ir

    ds = DiagramScribe(llm=mock_llm, output_path=str(output))
    with patch("diagram_scribe.adapters.backend.mermaid.webbrowser.open"):
        ds.draw("user login flow with decisions")

    assert output.exists()
    data = json.loads(output.read_text())
    assert data["type"] == "excalidraw"
    nodes = [e for e in data["elements"] if e["type"] not in ("arrow", "text", "line")]
    assert len(nodes) >= 3, "Expected at least 3 shapes (submit, decision, outcomes)"
    labels = [e["text"] for e in data["elements"] if e["type"] == "text"]
    assert any("dashboard" in l.lower() or "valid" in l.lower() for l in labels)


@pytest.mark.integration
def test_example_prompt_architecture_ecommerce(tmp_path):
    """README example: e-commerce system architecture with microservices."""
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    from diagram_scribe.models import MermaidIR

    output = tmp_path / "ecommerce_arch.excalidraw"
    ir = MermaidIR(
        source=(
            "flowchart TD\n"
            "  GW[API Gateway]\n"
            "  GW --> Auth[Auth Service]\n"
            "  GW --> Order[Order Service]\n"
            "  GW --> Notif[Notification Service]\n"
            "  Auth --> PG[(PostgreSQL)]\n"
            "  Order --> Mongo[(MongoDB)]\n"
            "  Order --> MQ[RabbitMQ]\n"
            "  MQ --> Notif\n"
            "  Notif --> Email[Email]"
        ),
        diagram_type="flowchart",
    )
    mock_llm = MagicMock()
    mock_llm.generate.return_value = ir

    ds = DiagramScribe(llm=mock_llm, output_path=str(output))
    with patch("diagram_scribe.adapters.backend.mermaid.webbrowser.open"):
        ds.draw("e-commerce platform architecture")

    assert output.exists()
    data = json.loads(output.read_text())
    assert data["type"] == "excalidraw"
    nodes = [e for e in data["elements"] if e["type"] not in ("arrow", "text", "line")]
    assert len(nodes) >= 5, "Expected at least 5 shapes"
    labels = [e["text"] for e in data["elements"] if e["type"] == "text"]
    assert any("gateway" in l.lower() or "auth" in l.lower() for l in labels)


@pytest.mark.integration
def test_example_prompt_sequence_login(tmp_path):
    """README example: UML sequence diagram for mobile app login."""
    if not shutil.which("node"):
        pytest.skip("Node.js not installed")

    from diagram_scribe.models import MermaidIR

    output = tmp_path / "login_sequence.excalidraw"
    ir = MermaidIR(
        source=(
            "sequenceDiagram\n"
            "    participant User\n"
            "    participant MobileApp as Mobile App\n"
            "    participant APIGateway as API Gateway\n"
            "    participant IdP as Identity Provider\n"
            "    User->>MobileApp: Enter credentials\n"
            "    MobileApp->>APIGateway: POST /auth (credentials)\n"
            "    APIGateway->>IdP: Validate credentials\n"
            "    IdP-->>APIGateway: JWT token\n"
            "    APIGateway-->>MobileApp: JWT token\n"
            "    MobileApp-->>User: Display home dashboard"
        ),
        diagram_type="sequence",
    )
    mock_llm = MagicMock()
    mock_llm.generate.return_value = ir

    ds = DiagramScribe(llm=mock_llm, output_path=str(output))
    with patch("diagram_scribe.adapters.backend.mermaid.webbrowser.open"):
        ds.draw("UML sequence diagram for mobile app login")

    assert output.exists()
    data = json.loads(output.read_text())
    assert data["type"] == "excalidraw"
    # Participant boxes (top + bottom) + lifelines + arrows
    boxes = [e for e in data["elements"] if e["type"] == "rectangle"]
    assert len(boxes) >= 4, "Expected at least 4 participant actor boxes"
    lifelines = [e for e in data["elements"] if e["type"] == "line"]
    assert len(lifelines) >= 4, "Expected at least 4 lifelines (one per participant)"
    labels = [e["text"] for e in data["elements"] if e["type"] == "text"]
    assert any("jwt" in l.lower() or "token" in l.lower() for l in labels)
    assert any("dashboard" in l.lower() or "home" in l.lower() for l in labels)


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
