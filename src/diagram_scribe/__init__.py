"""DiagramScribe — turn natural language descriptions into diagrams.

Quick start (requires ``OPENROUTER_API_KEY``)::

    from diagram_scribe import DiagramScribe

    ds = DiagramScribe()
    ds.draw("CI/CD pipeline — push code, run tests, deploy to staging.")
    ds.refine("add a manual approval step before deploy")

Public API:

- :class:`DiagramScribe` — main class, wires LLM + backend adapters
- :class:`~diagram_scribe.models.DiagramIR` — intermediate representation
- :class:`~diagram_scribe.models.Node` — a node in a diagram
- :class:`~diagram_scribe.models.Edge` — a directed edge between nodes
- :class:`~diagram_scribe.adapters.llm.openrouter.OpenRouterAdapter` — OpenRouter (default)
- :class:`~diagram_scribe.adapters.llm.ollama.OllamaAdapter` — local Ollama
- :class:`~diagram_scribe.adapters.llm.claude.ClaudeAdapter` — Anthropic API (``pip install diagram-scribe[claude]``)
- :class:`~diagram_scribe.adapters.backend.excalidraw.ExcalidrawAdapter` — Excalidraw

See ``docs/guide.md`` for full setup and usage instructions.
"""
from .core import DiagramScribe
from .models import Node, Edge, DiagramIR
from .adapters.llm.openrouter import OpenRouterAdapter
from .adapters.backend.excalidraw import ExcalidrawAdapter

__all__ = [
    "DiagramScribe",
    "Node", "Edge", "DiagramIR",
    "OpenRouterAdapter",
    "ExcalidrawAdapter",
]
