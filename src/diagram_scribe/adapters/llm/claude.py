from __future__ import annotations
import os
import anthropic
from ...models import DiagramIR
from ...prompts import SYSTEM_PROMPT, build_generate_messages, build_refine_messages, parse_ir_response


class ClaudeAdapter:
    """LLM adapter that calls the Anthropic API directly.

    This is the default adapter when ``ANTHROPIC_API_KEY`` is set. It uses
    ``claude-haiku-4-5-20251001`` by default — fast and cheap for structured
    JSON generation tasks.

    Args:
        api_key: Anthropic API key. Reads ``ANTHROPIC_API_KEY`` from the
            environment if not provided.
        model: Anthropic model ID to use.

    Example::

        from diagram_scribe.adapters.llm.claude import ClaudeAdapter
        adapter = ClaudeAdapter()  # reads ANTHROPIC_API_KEY from env
        ir = adapter.generate("login flow")
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model or os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

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
