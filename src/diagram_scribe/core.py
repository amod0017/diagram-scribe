"""DiagramScribe core — wires LLM and backend adapters together.

This is the main entry point for library users. Instantiate
:class:`DiagramScribe`, call :meth:`DiagramScribe.draw` with a description,
then call :meth:`DiagramScribe.refine` as many times as needed.

Default adapters are selected from environment variables when no
explicit adapter is passed. See :mod:`diagram_scribe.cli` for how the
CLI picks adapters.
"""
from __future__ import annotations
from .models import DiagramIR, MermaidIR
from .protocols import LLMAdapter, BackendAdapter


class DiagramScribe:
    """Orchestrates diagram generation and refinement.

    Routes LLM output to the appropriate backend: ``ExcalidrawAdapter`` for
    ``DiagramIR`` (simple spatial diagrams) or ``MermaidAdapter`` for
    ``MermaidIR`` (flowcharts, sequence diagrams, ER diagrams, class diagrams).

    Args:
        llm: An LLM adapter. Defaults to ``OpenRouterAdapter`` using env vars.
        backend: A backend adapter for the graph path. Defaults to
            ``ExcalidrawAdapter``. Used directly in tests to inject mocks.
        output_path: Output ``.excalidraw`` file path. Passed to both
            ``ExcalidrawAdapter`` and ``MermaidAdapter``.

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
        output_path: str | None = None,
    ):
        self._llm = llm or self._default_llm()
        self._output_path = output_path
        self._excalidraw_backend = backend or self._default_backend(output_path)
        self._mermaid_backend: object | None = None
        self._current_ir: DiagramIR | MermaidIR | None = None

    @staticmethod
    def _default_llm() -> LLMAdapter:
        import os
        from .adapters.llm.openrouter import OpenRouterAdapter
        return OpenRouterAdapter(
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            model=os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-super-49b-v1:free"),
        )

    @staticmethod
    def _default_backend(output_path: str | None = None) -> BackendAdapter:
        from .adapters.backend.excalidraw import ExcalidrawAdapter
        return ExcalidrawAdapter(output_path=output_path)

    def _get_mermaid_backend(self) -> object:
        if self._mermaid_backend is None:
            from .adapters.backend.mermaid import MermaidAdapter
            self._mermaid_backend = MermaidAdapter(output_path=self._output_path)
        return self._mermaid_backend

    def _render(self, ir: DiagramIR | MermaidIR) -> None:
        if isinstance(ir, MermaidIR):
            self._get_mermaid_backend().render(ir)
        else:
            self._excalidraw_backend.render(ir)

    def draw(self, description: str) -> DiagramIR | MermaidIR:
        """Generate a new diagram from a natural language description.

        The LLM decides the output format (Mermaid or graph). The appropriate
        backend renders and saves the result as a ``.excalidraw`` file.

        Args:
            description: Plain English description of the diagram to create.

        Returns:
            The generated ``DiagramIR`` or ``MermaidIR``.
        """
        self._current_ir = self._llm.generate(description)
        self._render(self._current_ir)
        return self._current_ir

    def refine(self, feedback: str) -> DiagramIR | MermaidIR:
        """Update the current diagram based on feedback.

        Must be called after :meth:`draw`. The LLM receives the current
        diagram state and the feedback, returns an updated IR of the same type,
        and the backend re-renders it.

        Args:
            feedback: Plain English instruction describing what to change.

        Returns:
            The updated ``DiagramIR`` or ``MermaidIR``.

        Raises:
            RuntimeError: If called before :meth:`draw`.
        """
        if self._current_ir is None:
            raise RuntimeError("Call draw() before refine()")
        self._current_ir = self._llm.refine(feedback, self._current_ir)
        self._render(self._current_ir)
        return self._current_ir
