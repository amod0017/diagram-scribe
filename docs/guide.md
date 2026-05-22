# DiagramScribe — User Guide

## What Is DiagramScribe?

DiagramScribe is a Python library and CLI tool that turns plain English descriptions into Excalidraw diagrams. You describe what you want — a flowchart, architecture diagram, sequence diagram, anything — and DiagramScribe generates it.

It works in two steps:

1. An LLM reads your description and produces a simple node/edge representation (called `DiagramIR`).
2. A backend adapter translates that representation into the target diagram format.

Both the LLM and the backend are swappable. The library ships with three LLM options (Claude, OpenRouter, Ollama) and one backend (Excalidraw). You can plug in your own.

---

## Installation

```bash
pip install diagram-scribe
```

For OpenRouter or Ollama support, install the extras:

```bash
pip install "diagram-scribe[openrouter]"   # OpenRouter (free + paid models)
pip install "diagram-scribe[ollama]"        # Ollama (fully local)
pip install "diagram-scribe[openrouter,ollama]"  # both
```

---

## Setup: Choosing an LLM

DiagramScribe needs an LLM to interpret your description. Three options:

### Option 1: Claude (recommended for quality)

Requires an [Anthropic API key](https://console.anthropic.com/).

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Or add it to a `.env` file in your working directory (the CLI loads this automatically):

```
ANTHROPIC_API_KEY=sk-ant-...
```

### Option 2: OpenRouter (free tier available)

[OpenRouter](https://openrouter.ai) provides access to hundreds of models under one API key. Free models are available with no credit card required.

```bash
pip install "diagram-scribe[openrouter]"
export OPENROUTER_API_KEY=sk-or-...
export OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free  # free model
```

Paid model example:

```bash
export OPENROUTER_MODEL=anthropic/claude-sonnet-4-6
```

Browse available models at [openrouter.ai/models](https://openrouter.ai/models). Free models have `:free` suffix.

### Option 3: Ollama (fully local, no account needed)

[Ollama](https://ollama.com) runs models on your machine. No internet required after the initial model download.

```bash
# install Ollama, then pull a model
ollama pull qwen2.5

pip install "diagram-scribe[ollama]"
export OLLAMA_MODEL=qwen2.5
```

Qwen2.5 is recommended — it produces reliable structured JSON output.

### .env file (CLI only)

The CLI loads a `.env` file from the current directory at startup. Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

```
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

---

## CLI Usage

Run the interactive session:

```bash
diagram-scribe
```

Example session:

```
DiagramScribe — describe your diagram in plain English.
Press Enter on an empty line to quit.

> Describe your diagram: CI/CD pipeline — push code, run tests, if tests pass
                          deploy to staging, run smoke tests, if smoke tests pass
                          deploy to production, otherwise notify the team.
Generating diagram...
[diagram opened]

> Refine (or press Enter to finish): add a manual approval step before production deploy
Updating diagram...
[diagram updated]

> Refine (or press Enter to finish): add a rollback path if production deploy fails
Updating diagram...
[diagram updated]

> Refine (or press Enter to finish):
Done.
```

The diagram opens as an `.excalidraw` file in your browser on the first call. Subsequent refinements update the same file — refresh the browser tab to see changes.

---

## Library Usage

### Basic: draw a diagram

```python
from diagram_scribe import DiagramScribe

ds = DiagramScribe()  # uses Claude by default (ANTHROPIC_API_KEY must be set)
ds.draw(
    "User authentication flow — user submits credentials, validate token, "
    "if valid return dashboard, if invalid increment retry count, "
    "if retries exceeded lock account."
)
```

### Iterative refinement

```python
from diagram_scribe import DiagramScribe

ds = DiagramScribe()
ds.draw(
    "CI/CD pipeline — push code, run tests, if tests pass deploy to staging, "
    "run smoke tests, if smoke tests pass deploy to production."
)

# user sees the diagram, wants changes
ds.refine("add a manual approval step before production deploy")
ds.refine("add a rollback path if production deploy fails")
```

Each `refine()` call sends the original description, the current diagram state, and your feedback to the LLM. The result replaces the current diagram.

### Using OpenRouter (free model)

```python
from diagram_scribe import DiagramScribe
from diagram_scribe.adapters.llm.openrouter import OpenRouterAdapter

ds = DiagramScribe(
    llm=OpenRouterAdapter(
        api_key="sk-or-...",
        model="meta-llama/llama-3.1-8b-instruct:free",
    )
)
ds.draw("Microservices architecture — API gateway routes to auth service, "
        "user service, and order service. Each service has its own database.")
```

### Using Ollama (local model)

```python
from diagram_scribe import DiagramScribe
from diagram_scribe.adapters.llm.ollama import OllamaAdapter

ds = DiagramScribe(llm=OllamaAdapter(model="qwen2.5"))
ds.draw("Git branching strategy — main branch, feature branches, "
        "pull request review, merge to main, tag release.")
```

### Saving to a custom file path

By default the diagram is saved to `~/.diagram-scribe/current.excalidraw`. To save elsewhere:

```python
from diagram_scribe import DiagramScribe
from diagram_scribe.adapters.backend.excalidraw import ExcalidrawAdapter

ds = DiagramScribe(backend=ExcalidrawAdapter(output_path="/tmp/my-diagram.excalidraw"))
ds.draw("Two microservices talking over a message queue.")
```

### Custom backend adapter

Implement the `BackendAdapter` protocol to render to any target:

```python
from diagram_scribe.models import DiagramIR


class MyAdapter:
    def render(self, ir: DiagramIR) -> None:
        for node in ir.nodes:
            print(f"Node {node.id}: {node.label} ({node.shape})")
        for edge in ir.edges:
            label = f" [{edge.label}]" if edge.label else ""
            print(f"Edge {edge.from_id} → {edge.to_id}{label}")


from diagram_scribe import DiagramScribe

ds = DiagramScribe(backend=MyAdapter())
ds.draw("Login flow — user submits form, validate credentials, return token.")
```

---

## Architecture

```
description (str)
        ↓
LLMAdapter.generate()  or  .refine()
        ↓
DiagramIR { nodes: list[Node], edges: list[Edge] }
        ↓
BackendAdapter.render()
        ↓
Diagram output (e.g. Excalidraw file)
```

### DiagramIR

The intermediate representation that decouples the LLM from the backend:

```python
@dataclass
class Node:
    id: str
    label: str
    shape: str  # "box", "diamond", "circle", "cylinder"

@dataclass
class Edge:
    from_id: str
    to_id: str
    label: str | None = None

@dataclass
class DiagramIR:
    nodes: list[Node]
    edges: list[Edge]
```

### Adapter protocols

```python
class LLMAdapter(Protocol):
    def generate(self, description: str) -> DiagramIR: ...
    def refine(self, feedback: str, current: DiagramIR) -> DiagramIR: ...

class BackendAdapter(Protocol):
    def render(self, ir: DiagramIR) -> None: ...
```

Any object that implements these methods works — no base class required.

### LLM adapter selection (CLI)

The CLI picks the LLM based on environment variables, in priority order:

1. `OPENROUTER_API_KEY` set → `OpenRouterAdapter`
2. `OLLAMA_MODEL` set → `OllamaAdapter`
3. `ANTHROPIC_API_KEY` set → `ClaudeAdapter`
4. None set → error with instructions

---

## Running Tests

Unit tests (no API keys needed):

```bash
pytest -v
```

Integration tests (require real API keys):

```bash
ANTHROPIC_API_KEY=sk-ant-... pytest -m integration -v
OPENROUTER_API_KEY=sk-or-... pytest -m integration -v
OLLAMA_MODEL=qwen2.5 pytest -m integration -v
```

---

## Contributing

1. Fork the repo and create a branch: `git checkout -b feat/my-feature`
2. Write a failing test first (TDD)
3. Implement the minimal code to make it pass
4. Run the full suite: `pytest -v`
5. Commit with a descriptive message and open a PR

New LLM adapters go in `src/diagram_scribe/adapters/llm/`. New backend adapters go in `src/diagram_scribe/adapters/backend/`. Follow the existing adapter pattern and add tests in `tests/`.
