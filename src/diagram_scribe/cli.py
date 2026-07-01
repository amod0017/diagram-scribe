"""Command-line interface for DiagramScribe.

Runs an interactive session: prompts for a description, calls ``draw()``,
then loops calling ``refine()`` until the user presses Enter on an empty line.

LLM selection priority (first match wins):

1. ``OPENROUTER_API_KEY`` set → :class:`~diagram_scribe.adapters.llm.openrouter.OpenRouterAdapter`
2. ``OLLAMA_MODEL`` set → :class:`~diagram_scribe.adapters.llm.ollama.OllamaAdapter`
3. ``ANTHROPIC_API_KEY`` set → :class:`~diagram_scribe.adapters.llm.claude.ClaudeAdapter`
4. None set → interactive first-run setup wizard

API keys can be set as environment variables or in a ``.env`` file.
Two locations are checked in order:

1. ``~/.config/diagram-scribe/.env`` — persistent user config (works from any directory)
2. ``.env`` in the current directory — per-project override
"""
from __future__ import annotations
import argparse
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
from .core import DiagramScribe
from .adapters.backend.excalidraw import ExcalidrawAdapter

_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "diagram-scribe")
_CONFIG_ENV = os.path.join(_CONFIG_DIR, ".env")

_DEFAULT_FREE_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"


def _fetch_free_models(api_key: str) -> list[str]:
    try:
        client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        models = client.models.list()
        free = sorted(
            m.id for m in models.data
            if m.id.endswith(":free")
        )
        return free if free else [_DEFAULT_FREE_MODEL]
    except Exception:
        return [_DEFAULT_FREE_MODEL]


def _fetch_ollama_models() -> list[str]:
    try:
        client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        models = client.models.list()
        return sorted(m.id for m in models.data)
    except Exception:
        return []


def _run_setup_wizard() -> None:
    """Interactive first-run setup — writes ~/.config/diagram-scribe/.env."""
    print("\nDiagramScribe needs an LLM. Let's get you set up.\n")
    print("Options:")
    print("  1. OpenRouter  (free models available, sign up at openrouter.ai)")
    print("  2. Ollama      (fully local, no account needed)")
    print("  3. Anthropic   (paid, pip install 'diagram-scribe[claude]')")
    print()

    while True:
        choice = input("Choose [1/2/3]: ").strip()
        if choice in ("1", "2", "3"):
            break
        print("Please enter 1, 2, or 3.")

    lines: list[str] = []

    if choice == "1":
        key = input("\nPaste your OpenRouter API key (sk-or-...): ").strip()
        if not key:
            print("No key entered. Exiting.")
            sys.exit(1)

        print("\nFetching available free models...")
        models = _fetch_free_models(key)

        print(f"\n{len(models)} free models available. Top picks:\n")
        display = models[:10]
        for i, m in enumerate(display, 1):
            print(f"  {i:2}. {m}")
        if len(models) > 10:
            print(f"  ... and {len(models) - 10} more")

        print()
        default_idx = next(
            (i + 1 for i, m in enumerate(display) if m == _DEFAULT_FREE_MODEL),
            1
        )
        while True:
            raw = input(f"Pick a model [1-{len(display)}, default={default_idx}]: ").strip()
            if raw == "":
                selected = display[default_idx - 1]
                break
            if raw.isdigit() and 1 <= int(raw) <= len(display):
                selected = display[int(raw) - 1]
                break
            print(f"Enter a number between 1 and {len(display)}.")

        lines = [
            f"OPENROUTER_API_KEY={key}",
            f"OPENROUTER_MODEL={selected}",
        ]
        os.environ["OPENROUTER_API_KEY"] = key
        os.environ["OPENROUTER_MODEL"] = selected
        print(f"\nUsing model: {selected}")

    elif choice == "2":
        print("\nFetching available Ollama models...")
        ollama_models = _fetch_ollama_models()
        if ollama_models:
            print(f"\n{len(ollama_models)} model(s) found:\n")
            for i, m in enumerate(ollama_models, 1):
                print(f"  {i:2}. {m}")
            print()
            while True:
                raw = input(f"Pick a model [1-{len(ollama_models)}]: ").strip()
                if raw.isdigit() and 1 <= int(raw) <= len(ollama_models):
                    model = ollama_models[int(raw) - 1]
                    break
                print(f"Enter a number between 1 and {len(ollama_models)}.")
        else:
            print("Could not connect to Ollama. Is it running? (ollama serve)")
            model = input("\nOllama model name (e.g. qwen2.5): ").strip()
        if not model:
            print("No model entered. Exiting.")
            sys.exit(1)
        lines = [f"OLLAMA_MODEL={model}"]
        os.environ["OLLAMA_MODEL"] = model

    elif choice == "3":
        key = input("\nPaste your Anthropic API key (sk-ant-...): ").strip()
        if not key:
            print("No key entered. Exiting.")
            sys.exit(1)
        lines = [f"ANTHROPIC_API_KEY={key}"]
        os.environ["ANTHROPIC_API_KEY"] = key

    os.makedirs(_CONFIG_DIR, exist_ok=True)
    with open(_CONFIG_ENV, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nConfig saved to {_CONFIG_ENV}")
    print("You won't need to set this up again.\n")


def _build_llm(model_override: str | None = None):
    if os.getenv("OPENROUTER_API_KEY"):
        from .adapters.llm.openrouter import OpenRouterAdapter
        model = model_override or os.getenv("OPENROUTER_MODEL", _DEFAULT_FREE_MODEL)
        return OpenRouterAdapter(api_key=os.environ["OPENROUTER_API_KEY"], model=model)

    if os.getenv("OLLAMA_MODEL"):
        from .adapters.llm.ollama import OllamaAdapter
        model = model_override or os.environ["OLLAMA_MODEL"]
        return OllamaAdapter(model=model)

    if os.getenv("ANTHROPIC_API_KEY"):
        from .adapters.llm.claude import ClaudeAdapter
        return ClaudeAdapter(model=model_override)

    return None


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="diagram-scribe",
        description="Turn natural language descriptions into Excalidraw diagrams.",
    )
    parser.add_argument("--key", metavar="API_KEY", help="OpenRouter API key (overrides .env)")
    parser.add_argument("--model", metavar="MODEL", help="Model to use for the active provider (overrides .env)")
    parser.add_argument("--output", metavar="PATH", help="Output .excalidraw file path (overrides DIAGRAM_SCRIBE_OUTPUT)")
    parser.add_argument(
        "--type", metavar="TYPE",
        choices=["flowchart", "sequence", "er", "architecture", "mindmap", "class"],
        help="Diagram type hint: flowchart, sequence, er, architecture, mindmap, class",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = _parse_args(argv)

    load_dotenv(_CONFIG_ENV)  # persistent user config (~/.config/diagram-scribe/.env)
    load_dotenv()              # per-project override (.env in CWD)

    if args.key:
        os.environ["OPENROUTER_API_KEY"] = args.key

    llm = _build_llm(model_override=args.model)
    if llm is None:
        _run_setup_wizard()
        llm = _build_llm(model_override=args.model)
        if llm is None:
            print("Setup failed. Exiting.")
            sys.exit(1)

    output_path = args.output or os.getenv("DIAGRAM_SCRIBE_OUTPUT")
    backend = ExcalidrawAdapter(output_path=output_path)
    ds = DiagramScribe(llm=llm, backend=backend, output_path=output_path)

    print("DiagramScribe — describe your diagram in plain English.")
    print("Press Enter on an empty line to quit.\n")

    description = input("> Describe your diagram: ").strip()
    if not description:
        return

    if args.type:
        description = f"[{args.type} diagram] {description}"

    print("Generating diagram...")
    try:
        ds.draw(description)
    except Exception as e:
        print(f"Failed to generate diagram: {e}")
        print("The LLM returned an unexpected response. Try rephrasing your description.")
        return
    print(f"[diagram saved to {backend._output_path}]\n")

    while True:
        feedback = input("> Refine (or press Enter to finish): ").strip()
        if not feedback:
            print("Done.")
            break
        print("Updating diagram...")
        try:
            ds.refine(feedback)
            print("[diagram updated]\n")
        except Exception as e:
            print(f"Failed to update diagram: {e}")
            print("Try rephrasing your feedback.")


if __name__ == "__main__":
    main()
