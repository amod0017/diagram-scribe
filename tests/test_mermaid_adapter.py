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


def test_mermaid_adapter_calls_node_subprocess(tmp_path):
    output = tmp_path / "out.excalidraw"
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = _fake_excalidraw_json()
    mock_result.stderr = ""

    with patch("diagram_scribe.adapters.backend.mermaid.subprocess.run", return_value=mock_result) as mock_run, \
         patch("diagram_scribe.adapters.backend.mermaid.webbrowser.open"):
        MermaidAdapter(output_path=str(output)).render(_simple_mermaid_ir())

    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert "node" in call_args[0][0]
    assert call_args[1]["input"] == "flowchart TD\n  A[Start] --> B[End]"


def test_mermaid_adapter_writes_excalidraw_file(tmp_path):
    output = tmp_path / "out.excalidraw"
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = _fake_excalidraw_json()
    mock_result.stderr = ""

    with patch("diagram_scribe.adapters.backend.mermaid.subprocess.run", return_value=mock_result), \
         patch("diagram_scribe.adapters.backend.mermaid.webbrowser.open"):
        MermaidAdapter(output_path=str(output)).render(_simple_mermaid_ir())

    assert output.exists()
    data = json.loads(output.read_text())
    assert data["type"] == "excalidraw"


def test_mermaid_adapter_opens_browser_on_first_render(tmp_path):
    output = tmp_path / "out.excalidraw"
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = _fake_excalidraw_json()
    mock_result.stderr = ""

    with patch("diagram_scribe.adapters.backend.mermaid.subprocess.run", return_value=mock_result), \
         patch("diagram_scribe.adapters.backend.mermaid.webbrowser.open") as mock_browser:
        adapter = MermaidAdapter(output_path=str(output))
        adapter.render(_simple_mermaid_ir())
        mock_browser.assert_called_once()
        adapter.render(_simple_mermaid_ir())
        assert mock_browser.call_count == 1


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
