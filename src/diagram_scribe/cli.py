from __future__ import annotations
import os
import sys
from dotenv import load_dotenv
from .core import DiagramScribe


def _build_llm():
    if os.getenv("OPENROUTER_API_KEY"):
        from .adapters.llm.openrouter import OpenRouterAdapter
        model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
        return OpenRouterAdapter(api_key=os.environ["OPENROUTER_API_KEY"], model=model)

    if os.getenv("OLLAMA_MODEL"):
        from .adapters.llm.ollama import OllamaAdapter
        return OllamaAdapter(model=os.environ["OLLAMA_MODEL"])

    if os.getenv("ANTHROPIC_API_KEY"):
        from .adapters.llm.claude import ClaudeAdapter
        return ClaudeAdapter()

    print(
        "Error: No LLM configured.\n"
        "Set one of: ANTHROPIC_API_KEY, OPENROUTER_API_KEY, or OLLAMA_MODEL\n"
        "Tip: create a .env file in the current directory — see .env.example"
    )
    sys.exit(1)


def main():
    load_dotenv()
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
