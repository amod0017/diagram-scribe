from unittest.mock import MagicMock, patch
from diagram_scribe.adapters.llm.ollama import OllamaAdapter
from diagram_scribe.models import DiagramIR, Node

_VALID_JSON = '{"nodes": [{"id": "a", "label": "Start", "shape": "circle"}], "edges": []}'


def _mock_response(text: str):
    return MagicMock(choices=[MagicMock(message=MagicMock(content=text))])


def test_generate_returns_diagram_ir():
    with patch("diagram_scribe.adapters.llm.ollama.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response(_VALID_JSON)

        adapter = OllamaAdapter(model="qwen2.5")
        ir = adapter.generate("a flow")

        assert isinstance(ir, DiagramIR)
        assert len(ir.nodes) == 1


def test_generate_uses_localhost_base_url():
    with patch("diagram_scribe.adapters.llm.ollama.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response(_VALID_JSON)

        OllamaAdapter(model="qwen2.5").generate("a flow")

        _, kwargs = mock_cls.call_args
        assert "localhost" in kwargs["base_url"]


def test_generate_uses_configured_model():
    with patch("diagram_scribe.adapters.llm.ollama.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response(_VALID_JSON)

        OllamaAdapter(model="llama3").generate("a flow")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "llama3"


def test_refine_returns_updated_ir():
    with patch("diagram_scribe.adapters.llm.ollama.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response(_VALID_JSON)

        adapter = OllamaAdapter(model="qwen2.5")
        current = DiagramIR(nodes=[Node("a", "A", "box")], edges=[])
        ir = adapter.refine("add a step", current)

        assert isinstance(ir, DiagramIR)
