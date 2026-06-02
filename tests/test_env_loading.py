import os
from unittest.mock import patch, MagicMock, call
from diagram_scribe.cli import main, _CONFIG_ENV


def test_main_loads_dotenv_before_building_llm():
    with patch("diagram_scribe.cli.load_dotenv") as mock_load, \
         patch("diagram_scribe.cli._build_llm", return_value=MagicMock()), \
         patch("diagram_scribe.cli.DiagramScribe", return_value=MagicMock()), \
         patch("builtins.input", side_effect=[""]):
        main([])
        mock_load.assert_called()


def test_main_loads_config_env_first():
    with patch("diagram_scribe.cli.load_dotenv") as mock_load, \
         patch("diagram_scribe.cli._build_llm", return_value=MagicMock()), \
         patch("diagram_scribe.cli.DiagramScribe", return_value=MagicMock()), \
         patch("builtins.input", side_effect=[""]):
        main([])
        first_call_arg = mock_load.call_args_list[0][0][0]
        assert first_call_arg == _CONFIG_ENV


def test_main_loads_cwd_dotenv_second():
    with patch("diagram_scribe.cli.load_dotenv") as mock_load, \
         patch("diagram_scribe.cli._build_llm", return_value=MagicMock()), \
         patch("diagram_scribe.cli.DiagramScribe", return_value=MagicMock()), \
         patch("builtins.input", side_effect=[""]):
        main([])
        assert mock_load.call_count == 2
        # second call is load_dotenv() with no args (CWD .env)
        second_call_args = mock_load.call_args_list[1][0]
        assert len(second_call_args) == 0


def test_config_env_path_is_in_home_config_dir():
    assert _CONFIG_ENV == os.path.join(
        os.path.expanduser("~"), ".config", "diagram-scribe", ".env"
    )
