"""DiagramScribe core — wires LLM and backend adapters together.

This is the main entry point for library users. Instantiate
:class:`DiagramScribe`, call :meth:`DiagramScribe.draw` with a description,
then call :meth:`DiagramScribe.refine` as many times as needed.

Default adapters are selected from environment variables when no
explicit adapter is passed. See :mod:`diagram_scribe.cli` for how the
CLI picks adapters.
"""
from __future__ import annotations
from .models import DiagramIR
from .protocols import LLMAdapter, BackendAdapter


class DiagramScribe:
    """Orchestrates diagram generation and refinement.

    Args:
        llm: An LLM adapter that implements :class:`~diagram_scribe.protocols.LLMAdapter`.
            Defaults to :class:`~diagram_scribe.adapters.llm.claude.ClaudeAdapter`
            (requires ``ANTHROPIC_API_KEY``).
        backend: A backend adapter that implements
            :class:`~diagram_scribe.protocols.BackendAdapter`.
            Defaults to :class:`~diagram_scribe.adapters.backend.excalidraw.ExcalidrawAdapter`.

    Example::

        from diagram_scribe import DiagramScribe

        ds = DiagramScribe()
        ds.draw("Two services: API gateway routes to user service.")
        ds.refine("add a database behind the user service")
    """

    def __init__(
        self,
        llm: LLMAdapter | None = None,
        backend: BackendAdapter | None = None,
    ):
        self._llm = llm or self._default_llm()
        self._backend = backend or self._default_backend()
        self._current_ir: DiagramIR | None = None

    @staticmethod
    def _default_llm() -> LLMAdapter:
        from .adapters.llm.claude import ClaudeAdapter
        return ClaudeAdapter()

    @staticmethod
    def _default_backend() -> BackendAdapter:
        from .adapters.backend.excalidraw import ExcalidrawAdapter
        return ExcalidrawAdapter()

    def draw(self, description: str) -> None:
        """Generate a new diagram from a natural language description.

        Replaces any previously drawn diagram. The LLM converts the
        description to a ``DiagramIR`` and the backend renders it.

        Args:
            description: Plain English description of the diagram to create.
        """
        self._current_ir = self._llm.generate(description)
        self._backend.render(self._current_ir)

    def refine(self, feedback: str) -> None:
        """Update the current diagram based on feedback.

        Must be called after :meth:`draw`. The LLM receives the current
        diagram state and the feedback, returns an updated ``DiagramIR``,
        and the backend re-renders it.

        Args:
            feedback: Plain English instruction describing what to change.

        Raises:
            RuntimeError: If called before :meth:`draw`.
        """
        if self._current_ir is None:
            raise RuntimeError("Call draw() before refine()")
        self._current_ir = self._llm.refine(feedback, self._current_ir)
        self._backend.render(self._current_ir)
