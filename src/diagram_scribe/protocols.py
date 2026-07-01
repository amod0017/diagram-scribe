from typing import Protocol
from .models import DiagramIR, MermaidIR


class LLMAdapter(Protocol):
    """Interface for LLM backends.

    Implementations translate natural language into a ``DiagramIR`` or
    ``MermaidIR`` depending on the diagram type. The three built-in
    implementations are :class:`ClaudeAdapter`, :class:`OpenRouterAdapter`,
    and :class:`OllamaAdapter`.

    To add a new LLM: implement ``generate`` and ``refine``, place the
    file in ``src/diagram_scribe/adapters/llm/``, and export it from
    ``src/diagram_scribe/__init__.py``.
    """

    def generate(self, description: str) -> DiagramIR | MermaidIR:
        """Convert a natural language description into a diagram.

        Args:
            description: Plain English description of the diagram to create.

        Returns:
            A ``DiagramIR`` for graph-path diagrams or a ``MermaidIR`` for
            Mermaid-path diagrams.
        """
        ...

    def refine(self, feedback: str, current: DiagramIR | MermaidIR) -> DiagramIR | MermaidIR:
        """Update an existing diagram based on user feedback.

        Args:
            feedback: Plain English instruction describing what to change.
            current: The current diagram state (either a ``DiagramIR`` or ``MermaidIR``).

        Returns:
            An updated diagram of the same type as ``current``.
        """
        ...


class BackendAdapter(Protocol):
    """Interface for diagram rendering backends.

    Implementations translate a diagram IR into a concrete file format.
    The built-in implementations are :class:`ExcalidrawAdapter` (graph path)
    and :class:`MermaidAdapter` (Mermaid path).

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
