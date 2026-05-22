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

DiagramScribe needs an LLM to interpret your description. By default it uses Claude (Anthropic API key required). No API key? Use a free model via [OpenRouter](https://openrouter.ai) or run one locally with [Ollama](https://ollama.com).

```bash
# Free via OpenRouter
OPENROUTER_API_KEY=... diagram-scribe

# Local via Ollama (no internet, no account)
OLLAMA_MODEL=qwen2.5 diagram-scribe
```

---

## Documentation

Full setup instructions, all LLM options, library examples, architecture overview, and contributing guide: **[docs/guide.md](docs/guide.md)**

---

## License

MIT
