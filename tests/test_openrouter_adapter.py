from unittest.mock import MagicMock, patch
from diagram_scribe.adapters.llm.openrouter import OpenRouterAdapter
from diagram_scribe.models import DiagramIR, Node

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
