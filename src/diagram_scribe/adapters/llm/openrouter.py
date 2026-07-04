from __future__ import annotations
from openai import OpenAI
from ...models import DiagramIR, MermaidIR
from ...prompts import (
    SYSTEM_PROMPT, build_generate_messages, build_refine_messages,
    build_mermaid_refine_messages, parse_response,
)


class OpenRouterAdapter:
    """LLM adapter that calls models via OpenRouter.

    OpenRouter provides access to hundreds of models — free and paid —
    under a single API key at https://openrouter.ai. The adapter uses the
    OpenAI-compatible chat completions endpoint.

    Free models have a ``:free`` suffix, e.g.
    ``meta-llama/llama-3.1-8b-instruct:free``. Browse models at
    https://openrouter.ai/models.

    Args:
        api_key: OpenRouter API key. Get one at https://openrouter.ai.
        model: Model ID to use. Defaults to
            ``"meta-llama/llama-3.1-8b-instruct:free"`` (free, no billing required).

    Example::

        from diagram_scribe.adapters.llm.openrouter import OpenRouterAdapter
        adapter = OpenRouterAdapter(api_key="sk-or-...", model="anthropic/claude-sonnet-4-6")
        ir = adapter.generate("CI/CD pipeline")
    """

    def __init__(
        self,
        api_key: str,
        model: str = "meta-llama/llama-3.1-8b-instruct:free",
    ):
        self._client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self._model = model

    def _call(self, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        )
        return response.choices[0].message.content

    def generate(self, description: str) -> DiagramIR | MermaidIR:
        return parse_response(self._call(build_generate_messages(description)))

    def refine(self, feedback: str, current: DiagramIR | MermaidIR) -> DiagramIR | MermaidIR:
        if isinstance(current, MermaidIR):
            return parse_response(self._call(build_mermaid_refine_messages(feedback, current)))
        return parse_response(self._call(build_refine_messages(feedback, current)))
