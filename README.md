# DiagramScribe

Describe a diagram in plain English. DiagramScribe generates it.

```bash
diagram-scribe
> Describe your diagram: CI/CD pipeline — push code, run tests, if tests pass deploy to
>                         staging, run smoke tests, if smoke tests pass deploy to production,
>                         otherwise notify the team.
> [diagram opens in Excalidraw]
> Refine (or press Enter to finish): add a manual approval step before production deploy
> [diagram updates]
> Refine (or press Enter to finish):
> Done.
```

Works as a CLI tool or as a Python library you can embed in your own project.

---

## Install

```bash
pip install diagram-scribe
```

---

## Usage

**CLI** — interactive, no code needed:
```bash
diagram-scribe
```

**Library** — embed in your own tool:
```python
from diagram_scribe import DiagramScribe

ds = DiagramScribe()
ds.draw("User authentication flow — user submits credentials, validate token, "
        "if valid return dashboard, if invalid increment retry count, "
        "if retries exceeded lock account.")
ds.refine("add a password reset path after account lock")
```

---

## LLM Options

DiagramScribe needs an LLM to interpret your description. By default it uses [OpenRouter](https://openrouter.ai) — free models available, no credit card required. Or run one locally with [Ollama](https://ollama.com) (no account needed).

```bash
# Free via OpenRouter (default) — sign up at openrouter.ai, create a key
OPENROUTER_API_KEY=sk-or-... diagram-scribe

# Local via Ollama (no internet, no account)
OLLAMA_MODEL=qwen2.5 diagram-scribe

# Claude via Anthropic (paid) — pip install "diagram-scribe[claude]"
ANTHROPIC_API_KEY=sk-ant-... diagram-scribe
```

---

## Documentation

- **[User Guide](docs/guide.md)** — setup, all LLM options, CLI and library examples, architecture
- **[API Reference](https://amod0017.github.io/diagram-scribe/)** — full class and method docs generated from source

---

## License

MIT
