from __future__ import annotations
from openai import OpenAI
from ...models import DiagramIR
from ...prompts import SYSTEM_PROMPT, build_generate_messages, build_refine_messages, parse_ir_response


class OllamaAdapter:
    """LLM adapter that calls a local Ollama server.

    Ollama (https://ollama.com) runs models on your machine with no
    internet access required after the initial model download. This
    adapter uses the OpenAI-compatible endpoint that Ollama exposes at
    ``http://localhost:11434``.

    Recommended model: ``qwen2.5`` — reliable structured JSON output for
    diagram generation tasks.

    Args:
        model: Ollama model name. Must already be pulled via ``ollama pull <model>``.
        base_url: Ollama server URL. Defaults to ``"http://localhost:11434/v1"``.

    Example::

        # terminal: ollama pull qwen2.5
        from diagram_scribe.adapters.llm.ollama import OllamaAdapter
        adapter = OllamaAdapter(model="qwen2.5")
        ir = adapter.generate("microservices architecture")
    """

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
