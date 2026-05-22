from unittest.mock import patch, MagicMock
from diagram_scribe.cli import main


def test_main_loads_dotenv_before_building_llm(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=from-dotenv-file\n")

    mock_ds = MagicMock()
    with patch("diagram_scribe.cli.load_dotenv") as mock_load, \
         patch("diagram_scribe.cli._build_llm", return_value=MagicMock()), \
         patch("diagram_scribe.cli.DiagramScribe", return_value=mock_ds), \
         patch("builtins.input", side_effect=[""]):
        main()
        mock_load.assert_called_once()
