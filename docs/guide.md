# DiagramScribe — User Guide

## What Is DiagramScribe?

DiagramScribe is a Python library and CLI tool that turns plain English descriptions into Excalidraw diagrams. You describe what you want — a flowchart, architecture diagram, sequence diagram, anything — and DiagramScribe generates it.

It works in two steps:

1. An AI model (called an LLM) reads your description and figures out what nodes and connections to draw.
2. DiagramScribe turns that into an Excalidraw file and opens it in your browser.

You need access to an AI model to use it. DiagramScribe supports three options — Claude, OpenRouter (free), and Ollama (local, no internet) — explained in the Setup section below.

---

## Installation

```bash
pip install diagram-scribe
```

OpenRouter and Ollama work out of the box. To use Claude (Anthropic), install the extra:

```bash
pip install "diagram-scribe[claude]"
```

---

## Setup: Choosing an LLM

### What is an LLM?

An LLM (Large Language Model) is a program that understands and generates text. DiagramScribe uses one to read your diagram description and figure out what nodes and connections to draw. You don't need to know how it works — you just need access to one.

There are three ways to get access:

| Option | Cost | Privacy | Setup effort |
|--------|------|---------|--------------|
| **OpenRouter** ✅ default, start here | Free tier available, no credit card | Your descriptions are sent to a cloud server | 5 minutes — sign up and copy a key |
| **Ollama** (privacy / offline) | Free forever | Everything stays on your machine | 10–15 minutes — needs 8 GB RAM and ~4 GB disk for the model download |
| **Claude** (highest quality) | Paid, ~$0.01–0.05 per diagram | Your descriptions are sent to Anthropic | 5 minutes — sign up and copy a key |

**Start with OpenRouter.** It's the default, takes 5 minutes, has free models, and works on any machine. Switch to Ollama later if you need everything to stay local, or Claude if you want the highest quality results.

---

### Option A: OpenRouter — free, no credit card required

OpenRouter is a website that gives you access to many AI models through a single account. Several models are completely free.

**Step 1 — Create an account**

Go to [openrouter.ai](https://openrouter.ai) and sign up. No credit card needed for free models.

**Step 2 — Create an API key**

1. Click your avatar (top right) → **Keys**
2. Click **Create key**, give it any name, click **Create**
3. Copy the key — it starts with `sk-or-v1-...`

**Step 3 — Set your key**

Create a file called `.env` in the folder where you run `diagram-scribe`:

```
OPENROUTER_API_KEY=sk-or-v1-...
```

That's it. DiagramScribe picks this up automatically when you run it.

**Recommended free models**

All of these are free on OpenRouter (`:free` suffix = no cost). Copy the model name exactly into your `.env`:

| Model | Set `OPENROUTER_MODEL=` | Notes |
|-------|------------------------|-------|
| Llama 3.1 8B by Meta | `meta-llama/llama-3.1-8b-instruct:free` | Default — good balance of quality and speed |
| Qwen 2.5 7B by Alibaba | `qwen/qwen-2.5-7b-instruct:free` | Excellent at following structured instructions |
| Gemma 2 9B by Google | `google/gemma-2-9b-it:free` | Higher quality, slightly slower |
| Mistral 7B | `mistralai/mistral-7b-instruct:free` | Fast and lightweight |

To use a specific model, add a second line to your `.env`:

```
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=qwen/qwen-2.5-7b-instruct:free
```

If you don't set `OPENROUTER_MODEL`, DiagramScribe uses Llama 3.1 8B by default.

You can browse all free models at [openrouter.ai/models](https://openrouter.ai/models) — filter by "Free" in the top right.

---

### Option B: Ollama — fully local, nothing leaves your machine

Ollama runs AI models on your own computer. After a one-time model download, it works completely offline. Good choice if you don't want your descriptions sent to any server.

**Requirements:** At least 8 GB of RAM. More RAM lets you run larger (better) models.

**Step 1 — Install Ollama**

Download and run the installer from [ollama.com](https://ollama.com). It works on Mac, Windows, and Linux.

After installing, Ollama runs in the background automatically. You'll see its icon in your system tray or menu bar.

**Step 2 — Download a model**

Open a terminal and run:

```bash
ollama pull qwen2.5
```

This downloads the model (about 4 GB). You only do this once.

**Step 3 — Tell DiagramScribe which model to use**

Create a `.env` file in the folder where you run `diagram-scribe`:

```
OLLAMA_MODEL=qwen2.5
```

No API key needed.

**Recommended local models**

| Model | Pull command | RAM needed | Notes |
|-------|-------------|------------|-------|
| Qwen 2.5 | `ollama pull qwen2.5` | 5 GB | Best choice — reliable structured output |
| Llama 3.2 | `ollama pull llama3.2` | 5 GB | Good general quality |
| Phi 3.5 Mini | `ollama pull phi3.5` | 3 GB | Smallest option — great if RAM is tight |
| Gemma 2 | `ollama pull gemma2` | 6 GB | Slightly higher quality |

To see what you've already downloaded: `ollama list`

---

### Option C: Claude — best quality

Requires a paid [Anthropic account](https://console.anthropic.com/). Typical cost is a few cents per diagram.

**Step 1 — Get an API key**

1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Go to **API Keys** → **Create Key**
3. Copy the key — it starts with `sk-ant-...`

**Step 2 — Set your key**

Create a `.env` file in the folder where you run `diagram-scribe`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

### .env file reference

The `.env` file goes in whichever folder you run `diagram-scribe` from. Create it with any text editor. Only set the lines for the option you chose:

```bash
# Option A — OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free   # optional, this is the default

# Option B — Ollama (no key needed)
OLLAMA_MODEL=qwen2.5

# Option C — Claude
ANTHROPIC_API_KEY=sk-ant-...
```

If you set multiple keys, DiagramScribe uses them in this priority order: OpenRouter → Ollama → Claude.

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

ds = DiagramScribe()  # uses OpenRouter by default (OPENROUTER_API_KEY must be set)
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

By default the diagram is saved to `~/Documents/diagram-scribe.excalidraw`. To save elsewhere:

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
