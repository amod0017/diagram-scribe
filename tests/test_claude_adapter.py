from unittest.mock import MagicMock, patch
from diagram_scribe.adapters.llm.claude import ClaudeAdapter
from diagram_scribe.models import DiagramIR, MermaidIR, Node

_VALID_JSON = '{"nodes": [{"id": "a", "label": "Start", "shape": "circle"}], "edges": []}'


def test_generate_returns_diagram_ir():
    with patch("diagram_scribe.adapters.llm.claude.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value.content = [MagicMock(text=_VALID_JSON)]

        adapter = ClaudeAdapter(api_key="test-key")
        ir = adapter.generate("a CI/CD flow")

        assert isinstance(ir, DiagramIR)
        assert len(ir.nodes) == 1
        assert ir.nodes[0].id == "a"
        mock_client.messages.create.assert_called_once()


def test_generate_passes_system_prompt():
    with patch("diagram_scribe.adapters.llm.claude.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value.content = [MagicMock(text=_VALID_JSON)]

        adapter = ClaudeAdapter(api_key="test-key")
        adapter.generate("a flow")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "system" in call_kwargs
        assert len(call_kwargs["system"]) > 0


def test_refine_passes_current_ir_in_message():
    with patch("diagram_scribe.adapters.llm.claude.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value.content = [MagicMock(text=_VALID_JSON)]

        adapter = ClaudeAdapter(api_key="test-key")
        current = DiagramIR(nodes=[Node("a", "A", "box")], edges=[])
        ir = adapter.refine("add a step", current)

        assert isinstance(ir, DiagramIR)
        call_kwargs = mock_client.messages.create.call_args.kwargs
        message_content = str(call_kwargs["messages"])
        assert "add a step" in message_content
        assert '"id": "a"' in message_content


def test_generate_returns_mermaid_ir_when_format_mermaid():
    mock_response = MagicMock()
    mock_response.content[0].text = "FORMAT: mermaid\nflowchart TD\n  A --> B"
    with patch("diagram_scribe.adapters.llm.claude.anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = mock_response
        adapter = ClaudeAdapter(api_key="test")
        result = adapter.generate("login flow")
    assert isinstance(result, MermaidIR)
