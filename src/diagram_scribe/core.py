from __future__ import annotations
from .models import DiagramIR
from .protocols import LLMAdapter, BackendAdapter


class DiagramScribe:
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
        self._current_ir = self._llm.generate(description)
        self._backend.render(self._current_ir)

    def refine(self, feedback: str) -> None:
        if self._current_ir is None:
            raise RuntimeError("Call draw() before refine()")
        self._current_ir = self._llm.refine(feedback, self._current_ir)
        self._backend.render(self._current_ir)
