"""Command-line interface for DiagramScribe.

Runs an interactive session: prompts for a description, calls ``draw()``,
then loops calling ``refine()`` until the user presses Enter on an empty line.

LLM selection priority (first match wins):

1. ``OPENROUTER_API_KEY`` set → :class:`~diagram_scribe.adapters.llm.openrouter.OpenRouterAdapter`
2. ``OLLAMA_MODEL`` set → :class:`~diagram_scribe.adapters.llm.ollama.OllamaAdapter`
3. ``ANTHROPIC_API_KEY`` set → :class:`~diagram_scribe.adapters.llm.claude.ClaudeAdapter`
4. None set → exits with an error message

API keys can be set as environment variables or in a ``.env`` file.
Two locations are checked in order:

1. ``~/.config/diagram-scribe/.env`` — persistent user config (works from any directory)
2. ``.env`` in the current directory — per-project override
"""
from __future__ import annotations
import os
import sys
from dotenv import load_dotenv
from .core import DiagramScribe

_CONFIG_ENV = os.path.join(os.path.expanduser("~"), ".config", "diagram-scribe", ".env")


def _build_llm():
    if os.getenv("OPENROUTER_API_KEY"):
        from .adapters.llm.openrouter import OpenRouterAdapter
        model = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
        return OpenRouterAdapter(api_key=os.environ["OPENROUTER_API_KEY"], model=model)

    if os.getenv("OLLAMA_MODEL"):
        from .adapters.llm.ollama import OllamaAdapter
        return OllamaAdapter(model=os.environ["OLLAMA_MODEL"])

    if os.getenv("ANTHROPIC_API_KEY"):
        from .adapters.llm.claude import ClaudeAdapter
        return ClaudeAdapter()

    print(
        "Error: No LLM configured.\n"
        "\n"
        "Quickest option — OpenRouter (free, no credit card):\n"
        "  1. Sign up at https://openrouter.ai\n"
        "  2. Create an API key under your avatar → Keys\n"
        "  3. Add to .env in this directory:  OPENROUTER_API_KEY=sk-or-...\n"
        "\n"
        "Other options: OLLAMA_MODEL=qwen2.5 (local), ANTHROPIC_API_KEY=sk-ant-... (paid)\n"
        "See docs/guide.md for full setup instructions."
    )
    sys.exit(1)


def main():
    load_dotenv(_CONFIG_ENV)  # persistent user config (~/.config/diagram-scribe/.env)
    load_dotenv()              # per-project override (.env in CWD)
    llm = _build_llm()
    ds = DiagramScribe(llm=llm)

    print("DiagramScribe — describe your diagram in plain English.")
    print("Press Enter on an empty line to quit.\n")

    description = input("> Describe your diagram: ").strip()
    if not description:
        return

    print("Generating diagram...")
    ds.draw(description)
    print("[diagram opened]\n")

    while True:
        feedback = input("> Refine (or press Enter to finish): ").strip()
        if not feedback:
            print("Done.")
            break
        print("Updating diagram...")
        ds.refine(feedback)
        print("[diagram updated]\n")


if __name__ == "__main__":
    main()
