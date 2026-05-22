from __future__ import annotations
import anthropic
from ...models import DiagramIR
from ...prompts import SYSTEM_PROMPT, build_generate_messages, build_refine_messages, parse_ir_response


class ClaudeAdapter:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-haiku-4-5-20251001",
    ):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def _call(self, messages: list[dict]) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text

    def generate(self, description: str) -> DiagramIR:
        return parse_ir_response(self._call(build_generate_messages(description)))

    def refine(self, feedback: str, current: DiagramIR) -> DiagramIR:
        return parse_ir_response(self._call(build_refine_messages(feedback, current)))
