import json
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from diagram_scribe.adapters.backend.mermaid import MermaidAdapter
from diagram_scribe.models import MermaidIR


def _simple_mermaid_ir():
    return MermaidIR(source="flowchart TD\n  A[Start] --> B[End]", diagram_type="flowchart")


def _fake_excalidraw_json():
    return json.dumps({
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [],
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    })


def _mock_node_run(stdout=None):
    r = MagicMock()
    r.returncode = 0
    r.stdout = stdout or _fake_excalidraw_json()
    r.stderr = ""
    return r


def test_mermaid_adapter_calls_node_subprocess(tmp_path):
    output = tmp_path / "out.excalidraw"
    with patch("diagram_scribe.adapters.backend.mermaid.subprocess.run",
               return_value=_mock_node_run()) as mock_run:
        MermaidAdapter(output_path=str(output)).render(_simple_mermaid_ir())
    mock_run.assert_called_once()
    assert "node" in mock_run.call_args[0][0]
    assert mock_run.call_args[1]["input"] == "flowchart TD\n  A[Start] --> B[End]"


def test_mermaid_adapter_writes_excalidraw_file(tmp_path):
    output = tmp_path / "out.excalidraw"
    with patch("diagram_scribe.adapters.backend.mermaid.subprocess.run",
               return_value=_mock_node_run()):
        MermaidAdapter(output_path=str(output)).render(_simple_mermaid_ir())
    assert output.exists()
    assert json.loads(output.read_text())["type"] == "excalidraw"


def test_mermaid_adapter_prints_saved_path(tmp_path, capsys):
    output = tmp_path / "out.excalidraw"
    with patch("diagram_scribe.adapters.backend.mermaid.subprocess.run",
               return_value=_mock_node_run()):
        MermaidAdapter(output_path=str(output)).render(_simple_mermaid_ir())
    assert str(output) in capsys.readouterr().out


def test_mermaid_adapter_raises_when_node_missing(tmp_path):
    output = tmp_path / "out.excalidraw"
    with patch("diagram_scribe.adapters.backend.mermaid.subprocess.run",
               side_effect=FileNotFoundError("node not found")):
        with pytest.raises(RuntimeError, match="Node.js"):
            MermaidAdapter(output_path=str(output)).render(_simple_mermaid_ir())


def test_mermaid_adapter_raises_on_nonzero_exit(tmp_path):
    output = tmp_path / "out.excalidraw"
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Parse error: invalid Mermaid"

    with patch("diagram_scribe.adapters.backend.mermaid.subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="Parse error"):
            MermaidAdapter(output_path=str(output)).render(_simple_mermaid_ir())
