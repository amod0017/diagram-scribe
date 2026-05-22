from __future__ import annotations
from openai import OpenAI
from ...models import DiagramIR
from ...prompts import SYSTEM_PROMPT, build_generate_messages, build_refine_messages, parse_ir_response


class OpenRouterAdapter:
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

    def generate(self, description: str) -> DiagramIR:
        return parse_ir_response(self._call(build_generate_messages(description)))

    def refine(self, feedback: str, current: DiagramIR) -> DiagramIR:
        return parse_ir_response(self._call(build_refine_messages(feedback, current)))
