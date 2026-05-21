from __future__ import annotations
from openai import OpenAI
from ...models import DiagramIR
from ...prompts import SYSTEM_PROMPT, build_generate_messages, build_refine_messages, parse_ir_response


class OllamaAdapter:
    def __init__(
        self,
        model: str = "qwen2.5",
        base_url: str = "http://localhost:11434/v1",
    ):
        self._client = OpenAI(base_url=base_url, api_key="ollama")
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
