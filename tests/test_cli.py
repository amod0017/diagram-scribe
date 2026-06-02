import os
import pytest
from unittest.mock import patch, MagicMock, call
from diagram_scribe.cli import main, _build_llm, _run_setup_wizard, _parse_args


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
         patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "OLLAMA_MODEL": ""}, clear=False):
        with patch("diagram_scribe.adapters.llm.claude.anthropic.Anthropic"):
            llm = _build_llm()
        assert "Claude" in type(llm).__name__


def test_build_llm_returns_none_when_no_key_configured():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "", "OPENROUTER_API_KEY": "", "OLLAMA_MODEL": ""}, clear=False):
        assert _build_llm() is None


def test_main_runs_setup_wizard_when_no_llm():
    mock_ds = MagicMock()
    mock_llm = MagicMock()
    with patch("diagram_scribe.cli._build_llm", side_effect=[None, mock_llm]), \
         patch("diagram_scribe.cli._run_setup_wizard") as mock_wizard, \
         patch("diagram_scribe.cli.DiagramScribe", return_value=mock_ds), \
         patch("diagram_scribe.cli.load_dotenv"), \
         patch("builtins.input", side_effect=[""]):
        main([])
        mock_wizard.assert_called_once()


def test_main_draws_on_first_input_and_quits_on_empty():
    mock_ds = MagicMock()
    with patch("diagram_scribe.cli._build_llm", return_value=MagicMock()), \
         patch("diagram_scribe.cli.DiagramScribe", return_value=mock_ds), \
         patch("diagram_scribe.cli.load_dotenv"), \
         patch("builtins.input", side_effect=["CI/CD pipeline flow", ""]):
        main([])

    mock_ds.draw.assert_called_once_with("CI/CD pipeline flow")
    mock_ds.refine.assert_not_called()


def test_main_refines_on_subsequent_inputs():
    mock_ds = MagicMock()
    with patch("diagram_scribe.cli._build_llm", return_value=MagicMock()), \
         patch("diagram_scribe.cli.DiagramScribe", return_value=mock_ds), \
         patch("diagram_scribe.cli.load_dotenv"), \
         patch("builtins.input", side_effect=["CI/CD flow", "add approval step", "rename deploy", ""]):
        main([])

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
        main([])

    mock_ds.draw.assert_not_called()


# --- setup wizard ---

def test_setup_wizard_openrouter_writes_config(tmp_path):
    config_env = tmp_path / ".env"
    with patch("diagram_scribe.cli._CONFIG_DIR", str(tmp_path)), \
         patch("diagram_scribe.cli._CONFIG_ENV", str(config_env)), \
         patch("diagram_scribe.cli._fetch_free_models", return_value=["model-a:free", "model-b:free"]), \
         patch("builtins.input", side_effect=["1", "sk-or-testkey", "1"]):
        _run_setup_wizard()

    content = config_env.read_text()
    assert "OPENROUTER_API_KEY=sk-or-testkey" in content
    assert "OPENROUTER_MODEL=model-a:free" in content


def test_setup_wizard_ollama_writes_config(tmp_path):
    config_env = tmp_path / ".env"
    with patch("diagram_scribe.cli._CONFIG_DIR", str(tmp_path)), \
         patch("diagram_scribe.cli._CONFIG_ENV", str(config_env)), \
         patch("builtins.input", side_effect=["2", "qwen2.5"]):
        _run_setup_wizard()

    assert "OLLAMA_MODEL=qwen2.5" in config_env.read_text()


def test_setup_wizard_anthropic_writes_config(tmp_path):
    config_env = tmp_path / ".env"
    with patch("diagram_scribe.cli._CONFIG_DIR", str(tmp_path)), \
         patch("diagram_scribe.cli._CONFIG_ENV", str(config_env)), \
         patch("builtins.input", side_effect=["3", "sk-ant-testkey"]):
        _run_setup_wizard()

    assert "ANTHROPIC_API_KEY=sk-ant-testkey" in config_env.read_text()


def test_setup_wizard_sets_env_vars(tmp_path):
    config_env = tmp_path / ".env"
    with patch("diagram_scribe.cli._CONFIG_DIR", str(tmp_path)), \
         patch("diagram_scribe.cli._CONFIG_ENV", str(config_env)), \
         patch("diagram_scribe.cli._fetch_free_models", return_value=["model-a:free"]), \
         patch("builtins.input", side_effect=["1", "sk-or-testkey", "1"]), \
         patch.dict(os.environ, {}, clear=False):
        _run_setup_wizard()
        assert os.environ.get("OPENROUTER_API_KEY") == "sk-or-testkey"


# --- CLI flags ---

def test_parse_args_defaults_are_none():
    args = _parse_args([])
    assert args.key is None
    assert args.model is None


def test_parse_args_key_flag():
    args = _parse_args(["--key", "sk-or-test"])
    assert args.key == "sk-or-test"


def test_parse_args_model_flag():
    args = _parse_args(["--model", "google/gemma-4-31b-it:free"])
    assert args.model == "google/gemma-4-31b-it:free"


def test_parse_args_both_flags():
    args = _parse_args(["--key", "sk-or-test", "--model", "nvidia/foo:free"])
    assert args.key == "sk-or-test"
    assert args.model == "nvidia/foo:free"


def test_key_flag_overrides_env(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    mock_ds = MagicMock()
    with patch("diagram_scribe.cli.load_dotenv"), \
         patch("diagram_scribe.cli.DiagramScribe", return_value=mock_ds), \
         patch("diagram_scribe.adapters.llm.openrouter.OpenAI"), \
         patch("builtins.input", side_effect=[""]):
        main(["--key", "sk-or-fromflag"])
    assert os.environ.get("OPENROUTER_API_KEY") == "sk-or-fromflag"


def test_model_flag_overrides_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-existing")
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    mock_ds = MagicMock()
    with patch("diagram_scribe.cli.load_dotenv"), \
         patch("diagram_scribe.cli.DiagramScribe", return_value=mock_ds), \
         patch("diagram_scribe.adapters.llm.openrouter.OpenAI"), \
         patch("builtins.input", side_effect=[""]):
        main(["--model", "google/gemma-4-31b-it:free"])
    assert os.environ.get("OPENROUTER_MODEL") == "google/gemma-4-31b-it:free"


def test_key_and_model_flags_together(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    mock_ds = MagicMock()
    with patch("diagram_scribe.cli.load_dotenv"), \
         patch("diagram_scribe.cli.DiagramScribe", return_value=mock_ds), \
         patch("diagram_scribe.adapters.llm.openrouter.OpenAI"), \
         patch("builtins.input", side_effect=[""]):
        main(["--key", "sk-or-test", "--model", "nvidia/foo:free"])
    assert os.environ.get("OPENROUTER_API_KEY") == "sk-or-test"
    assert os.environ.get("OPENROUTER_MODEL") == "nvidia/foo:free"
