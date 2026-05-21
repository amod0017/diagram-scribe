from typing import Protocol
from .models import DiagramIR


class LLMAdapter(Protocol):
    def generate(self, description: str) -> DiagramIR: ...
    def refine(self, feedback: str, current: DiagramIR) -> DiagramIR: ...


class BackendAdapter(Protocol):
    def render(self, ir: DiagramIR) -> None: ...
