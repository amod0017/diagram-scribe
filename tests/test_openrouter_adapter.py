from unittest.mock import MagicMock, patch
from diagram_scribe.adapters.llm.openrouter import OpenRouterAdapter
from diagram_scribe.models import DiagramIR, MermaidIR, Node

_VALID_JSON = '{"nodes": [{"id": "a", "label": "Start", "shape": "circle"}], "edges": []}'


def _mock_response(text: str):
    return MagicMock(choices=[MagicMock(message=MagicMock(content=text))])


def test_generate_returns_diagram_ir():
    with patch("diagram_scribe.adapters.llm.openrouter.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response(_VALID_JSON)

        adapter = OpenRouterAdapter(api_key="test-key")
        ir = adapter.generate("a flow")

        assert isinstance(ir, DiagramIR)
        assert len(ir.nodes) == 1


def test_generate_uses_openrouter_base_url():
    with patch("diagram_scribe.adapters.llm.openrouter.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response(_VALID_JSON)

        OpenRouterAdapter(api_key="test-key").generate("a flow")

        _, kwargs = mock_cls.call_args
        assert "openrouter.ai" in kwargs["base_url"]


def test_generate_uses_configured_model():
    with patch("diagram_scribe.adapters.llm.openrouter.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response(_VALID_JSON)

        OpenRouterAdapter(api_key="test-key", model="my/model").generate("a flow")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "my/model"


def test_refine_returns_updated_ir():
    with patch("diagram_scribe.adapters.llm.openrouter.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response(_VALID_JSON)

        adapter = OpenRouterAdapter(api_key="test-key")
        current = DiagramIR(nodes=[Node("a", "A", "box")], edges=[])
        ir = adapter.refine("add a step", current)

        assert isinstance(ir, DiagramIR)


def test_generate_returns_mermaid_ir_when_format_mermaid():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "FORMAT: mermaid\nflowchart TD\n  A --> B"
    )
    with patch("diagram_scribe.adapters.llm.openrouter.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        adapter = OpenRouterAdapter(api_key="test", model="test-model")
        result = adapter.generate("login flow")
    assert isinstance(result, MermaidIR)
    assert "flowchart TD" in result.source


def test_refine_passes_mermaid_ir_correctly():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "FORMAT: mermaid\nflowchart TD\n  A --> B --> C"
    )
    current = MermaidIR(source="flowchart TD\n  A --> B", diagram_type="flowchart")
    with patch("diagram_scribe.adapters.llm.openrouter.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        adapter = OpenRouterAdapter(api_key="test", model="test-model")
        result = adapter.refine("add C node", current)
    assert isinstance(result, MermaidIR)
