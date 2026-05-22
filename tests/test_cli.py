import os
import pytest
from unittest.mock import patch, MagicMock
from diagram_scribe.cli import main, _build_llm


def test_build_llm_uses_openrouter_when_key_set():
    env = {"OPENROUTER_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=False), \
         patch.dict(os.environ, {"OLLAMA_MODEL": ""}, clear=False), \
         patch("diagram_scribe.adapters.llm.openrouter.OpenAI"):
        llm = _build_llm()
        assert "OpenRouter" in type(llm).__name__


def test_build_llm_uses_ollama_when_model_set():
    env = {"OLLAMA_MODEL": "qwen2.5"}
    with patch.dict(os.environ, env, clear=False), \
         patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=False), \
         patch("diagram_scribe.adapters.llm.ollama.OpenAI"):
        llm = _build_llm()
        assert "Ollama" in type(llm).__name__


def test_build_llm_uses_claude_when_anthropic_key_set():
    env = {"ANTHROPIC_API_KEY": "test-key"}
    with patch.dict(os.environ, env, clear=False), \
         patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "OLLAMA_MODEL": ""}, clear=False), \
         patch("diagram_scribe.adapters.llm.claude.anthropic.Anthropic"):
        llm = _build_llm()
        assert "Claude" in type(llm).__name__


def test_build_llm_exits_when_no_key_configured():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "", "OPENROUTER_API_KEY": "", "OLLAMA_MODEL": ""}, clear=False):
        with pytest.raises(SystemExit):
            _build_llm()


def test_main_draws_on_first_input_and_quits_on_empty():
    mock_ds = MagicMock()
    with patch("diagram_scribe.cli._build_llm", return_value=MagicMock()), \
         patch("diagram_scribe.cli.DiagramScribe", return_value=mock_ds), \
         patch("diagram_scribe.cli.load_dotenv"), \
         patch("builtins.input", side_effect=["CI/CD pipeline flow", ""]):
        main()

    mock_ds.draw.assert_called_once_with("CI/CD pipeline flow")
    mock_ds.refine.assert_not_called()


def test_main_refines_on_subsequent_inputs():
    mock_ds = MagicMock()
    with patch("diagram_scribe.cli._build_llm", return_value=MagicMock()), \
         patch("diagram_scribe.cli.DiagramScribe", return_value=mock_ds), \
         patch("diagram_scribe.cli.load_dotenv"), \
         patch("builtins.input", side_effect=["CI/CD flow", "add approval step", "rename deploy", ""]):
        main()

    mock_ds.draw.assert_called_once_with("CI/CD flow")
    assert mock_ds.refine.call_count == 2
    mock_ds.refine.assert_any_call("add approval step")
    mock_ds.refine.assert_any_call("rename deploy")


def test_main_quits_immediately_on_empty_description():
    mock_ds = MagicMock()
    with patch("diagram_scribe.cli._build_llm", return_value=MagicMock()), \
         patch("diagram_scribe.cli.DiagramScribe", return_value=mock_ds), \
         patch("diagram_scribe.cli.load_dotenv"), \
         patch("builtins.input", side_effect=[""]):
        main()

    mock_ds.draw.assert_not_called()
