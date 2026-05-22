from typing import Protocol
from .models import DiagramIR


class LLMAdapter(Protocol):
    """Interface for LLM backends.

    Implementations translate natural language into ``DiagramIR``.
    The three built-in implementations are :class:`ClaudeAdapter`,
    :class:`OpenRouterAdapter`, and :class:`OllamaAdapter`.

    To add a new LLM: implement ``generate`` and ``refine``, place the
    file in ``src/diagram_scribe/adapters/llm/``, and export it from
    ``src/diagram_scribe/__init__.py``.
    """

    def generate(self, description: str) -> DiagramIR:
        """Convert a natural language description into a diagram.

        Args:
            description: Plain English description of the diagram to create.

        Returns:
            A ``DiagramIR`` with nodes and edges extracted from the description.
        """
        ...

    def refine(self, feedback: str, current: DiagramIR) -> DiagramIR:
        """Update an existing diagram based on user feedback.

        The LLM receives the original description, the current ``DiagramIR``
        serialised as JSON, and the feedback string. It returns a new
        ``DiagramIR`` that incorporates the requested changes.

        Args:
            feedback: Plain English instruction describing what to change.
            current: The diagram state to modify.

        Returns:
            An updated ``DiagramIR``.
        """
        ...


class BackendAdapter(Protocol):
    """Interface for diagram rendering backends.

    Implementations translate a ``DiagramIR`` into a concrete diagram
    format (e.g. Excalidraw JSON). The built-in implementation is
    :class:`ExcalidrawAdapter`.

    To add a new backend: implement ``render``, place the file in
    ``src/diagram_scribe/adapters/backend/``, and export it from
    ``src/diagram_scribe/__init__.py``.
    """

    def render(self, ir: DiagramIR) -> None:
        """Render a diagram from its intermediate representation.

        Args:
            ir: The diagram to render.
        """
        ...
