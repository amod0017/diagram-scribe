"""Mermaid backend adapter.

Converts a ``MermaidIR`` to Excalidraw JSON by invoking a pre-built Node.js
bundle via subprocess. The bundle uses ``@excalidraw/mermaid-to-excalidraw``
to do the conversion. Node.js >=18 must be installed.

Output is written to the same ``.excalidraw`` path used by ``ExcalidrawAdapter``.
"""
from __future__ import annotations
import json
import os
import subprocess
import webbrowser
from pathlib import Path
from ...models import MermaidIR

_DEFAULT_PATH = os.path.join(os.path.expanduser("~"), "Documents", "diagram-scribe.excalidraw")
_BUNDLE: Path = Path(__file__).parent.parent.parent / "js" / "mermaid_to_excalidraw.bundle.js"


class MermaidAdapter:
    """Backend adapter that converts Mermaid text to Excalidraw via Node.js.

    Args:
        output_path: Path to write the ``.excalidraw`` file. Defaults to
            ``~/Documents/diagram-scribe.excalidraw``.

    Raises:
        RuntimeError: If Node.js is not installed or the Mermaid source is invalid.
    """

    def __init__(self, output_path: str | None = None):
        self._output_path = output_path or _DEFAULT_PATH
        self._opened = False

    def render(self, ir: MermaidIR) -> None:
        try:
            result = subprocess.run(
                ["node", str(_BUNDLE)],
                input=ir.source,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "Node.js is required to render this diagram type. "
                "Install from https://nodejs.org (version 18 or later)."
            )

        if result.returncode != 0:
            raise RuntimeError(
                f"Mermaid conversion failed: {result.stderr.strip() or 'unknown error'}"
            )

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON from Mermaid converter: {e}")
        os.makedirs(os.path.dirname(self._output_path), exist_ok=True)
        with open(self._output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        if not self._opened:
            webbrowser.open(f"file://{os.path.abspath(self._output_path)}")
            self._opened = True
        else:
            print("Diagram updated — refresh your browser tab to see changes.")
