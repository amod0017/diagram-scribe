# Design: Mermaid Dual-Path Rendering

**Date:** 2026-06-30
**Status:** Approved

## Problem

The current diagram-scribe pipeline routes all diagram types through a hand-rolled topological layout engine (`_layout()` in `excalidraw.py`). This engine places nodes in a simple BFS-level grid. It works acceptably for small spatial diagrams (3–5 nodes) but breaks down completely for complex flows: nodes overlap, parallel branches collapse into a single vertical chain, and back-edges (retry loops) produce arrows spanning thousands of pixels.

The root cause is not the LLM output — it is trying to do layout ourselves. PlantUML and Mermaid have spent years building layout engines (Graphviz/ELK/Dagre) for exactly this problem. We should use them.

## Goal

`diagram-scribe` should be able to draw everything — from a simple 3-tier architecture to a 25-step auth flowchart with parallel branches and retry loops — and produce a clean, readable `.excalidraw` file in all cases.

## Decision

Use a dual-path rendering pipeline:

- **Graph path** (existing): LLM returns DiagramIR JSON → `ExcalidrawAdapter` renders with our layout engine. Best for simple spatial diagrams (architecture, mindmaps, small flows).
- **Mermaid path** (new): LLM returns Mermaid text → `MermaidAdapter` converts via a bundled Node.js script → writes `.excalidraw`. Best for complex flows, sequence diagrams, ER diagrams, class diagrams.

The LLM decides which path to use by prefixing its response with `FORMAT: mermaid` or `FORMAT: graph`. This requires no extra LLM call. The `--type` flag overrides by including the type in the description, which biases the LLM toward the expected format. The output is always a `.excalidraw` file — the user never sees the routing.

## Architecture

```
User / CLI
    │  description (+ optional --type hint)
    ▼
core.py  ──── LLM Adapter (OpenRouter / Ollama / Claude)
    │              │  raw text with FORMAT header
    │         parse_response()
    │              │  DiagramIR | MermaidIR
    ▼              ▼
DiagramScribe routes by IR type
    │                        │
    ▼                        ▼
ExcalidrawAdapter       MermaidAdapter
(DiagramIR → JSON)      (MermaidIR → Node.js subprocess)
    │                        │
    └──────────┬─────────────┘
               ▼
       diagram-scribe.excalidraw
```

## Components

### 1. `models.py` — add `MermaidIR`

```python
@dataclass
class MermaidIR:
    source: str          # raw Mermaid text
    diagram_type: str    # e.g. "flowchart", "sequence" — for logging
```

`DiagramIR`, `Node`, `Edge` are unchanged.

### 2. `prompts.py` — unified system prompt + response parser

**System prompt change:** prepend a routing instruction:

> "First line of your response MUST be either `FORMAT: mermaid` or `FORMAT: graph`.
> Choose `mermaid` for flowcharts, sequence diagrams, ER diagrams, and class diagrams.
> Choose `graph` for architecture diagrams, mindmaps, and simple spatial layouts.
> After the FORMAT line, output either Mermaid code or DiagramIR JSON."

The Mermaid shape/diagram-type guide and the DiagramIR schema are both included in the prompt so the LLM knows both formats.

**New function:**

```python
def parse_response(text: str) -> DiagramIR | MermaidIR:
    """Strip FORMAT header, dispatch to the right parser."""
```

`parse_ir_response()` is kept unchanged — `parse_response()` calls it for the graph path.

`build_generate_messages()` is unchanged.

`build_refine_messages(feedback, current: DiagramIR)` is unchanged for the graph path.

A new `build_mermaid_refine_messages(feedback, current: MermaidIR)` is added for the Mermaid path. It includes `current.source` as plain text (not JSON) so the LLM can produce an updated Mermaid diagram.

### 3. LLM adapters — updated return type

All three adapters (`OpenRouterAdapter`, `OllamaAdapter`, `ClaudeAdapter`) change:

- `generate(description) -> DiagramIR | MermaidIR`
- `refine(feedback, current) -> DiagramIR | MermaidIR`

Where `current` is now `DiagramIR | MermaidIR`. The body changes from `parse_ir_response(...)` to `parse_response(...)`. No other changes.

The `LLMAdapter` protocol is updated to reflect the new return types.

### 4. `core.py` — runtime routing

`DiagramScribe` selects the backend at render time based on the IR type:

```python
def _render(self, ir: DiagramIR | MermaidIR) -> None:
    if isinstance(ir, MermaidIR):
        MermaidAdapter(output_path=self._output_path).render(ir)
    else:
        self._excalidraw_backend.render(ir)
```

`DiagramScribe.__init__` gains an `output_path: str | None` parameter (defaulting to `None`, which means each adapter uses its own default). It stores `self._output_path` and passes it when constructing both `ExcalidrawAdapter` (existing graph path) and `MermaidAdapter` (on demand). The existing `backend` parameter is kept for tests that inject a mock backend; when a mock backend is provided, `output_path` is ignored.

`draw()` and `refine()` signatures are unchanged. They still return `DiagramIR | MermaidIR`.

### 5. `adapters/backend/mermaid.py` — new adapter

```python
class MermaidAdapter:
    def __init__(self, output_path: str | None = None): ...
    def render(self, ir: MermaidIR) -> None: ...
```

`render()`:
1. Locates the bundled JS file (`diagram_scribe/js/mermaid_to_excalidraw.bundle.js`)
2. Invokes `node <bundle> --stdin` via `subprocess.run`, piping `ir.source`
3. Parses stdout as Excalidraw JSON
4. Writes to `output_path`
5. Opens browser on first call (same as `ExcalidrawAdapter`)

**Error handling:**
- If `node` is not on PATH: raises `RuntimeError("Node.js is required for this diagram type. Install from nodejs.org.")`
- If the bundle exits non-zero: raises `RuntimeError` with the stderr output
- If the LLM output is invalid Mermaid: the Node.js bundle exits non-zero; the error is surfaced to the user via the existing try/except in `cli.py`

### 6. `js/mermaid_to_excalidraw.bundle.js` — Node.js converter

A pre-built single-file bundle created with `esbuild` from `@excalidraw/mermaid-to-excalidraw`. Reads Mermaid text from stdin, writes Excalidraw JSON to stdout.

The bundle is committed to the repo under `src/diagram_scribe/js/`. Users need Node.js ≥18 but do not need npm or any separate install step.

The bundle is rebuilt by maintainers when `@excalidraw/mermaid-to-excalidraw` is updated. A `package.json` and `build.js` (esbuild script) live in `js/` for this purpose but are not shipped in the Python package.

### 7. `cli.py` — minimal changes

- `--type` flag values are passed as a prefix in the description: `[flowchart diagram] <description>`. The LLM uses this to bias its FORMAT choice. No Python-level format forcing.
- Error handling for `MermaidAdapter` failures (Node.js missing, bad Mermaid) is caught by the existing try/except around `ds.draw()` / `ds.refine()`.
- No new flags needed.

### 8. `pyproject.toml`

Add Node.js ≥18 to the documentation/README as a runtime requirement. It is not expressible as a pip dependency; document it clearly.

## Data Flow: Mermaid Path (example)

```
Input:  "user login flow with email and OAuth"

LLM response:
  FORMAT: mermaid
  flowchart TD
    start([Start]) --> login[Login Screen]
    login --> choose{Auth Method}
    choose -->|email| validate[Validate Email]
    choose -->|oauth| provider[Redirect to Provider]
    ...

parse_response() returns:
  MermaidIR(source="flowchart TD\n...", diagram_type="flowchart")

MermaidAdapter:
  node bundle.js --stdin < mermaid_source
  stdout -> Excalidraw JSON
  write -> ~/Documents/diagram-scribe.excalidraw
```

## What Does Not Change

- `ExcalidrawAdapter` and its layout engine — untouched
- `build_generate_messages()` / `build_refine_messages()` signatures
- `DiagramIR`, `Node`, `Edge`
- All three LLM adapter constructors
- CLI UX (setup wizard, `--key`, `--model`, `--output`, `--type`)
- All existing unit tests for the graph path

## Testing

**Unit tests (no Node.js needed):**
- `test_parse_response_mermaid_format()` — FORMAT: mermaid header → MermaidIR
- `test_parse_response_graph_format()` — FORMAT: graph header → DiagramIR
- `test_parse_response_falls_back_to_graph()` — missing header → DiagramIR (backward compat)
- `test_core_routes_mermaid_ir_to_mermaid_adapter()` — mock both adapters, assert correct one called
- `test_mermaid_adapter_raises_on_missing_node()` — mock subprocess, assert RuntimeError

**Integration tests (`@pytest.mark.integration`):**
- `test_mermaid_path_end_to_end()` — real LLM, real Node.js, assert valid `.excalidraw` output
- Requires Node.js ≥18 on the test runner

## Open Issues Resolved by This Change

- **#61** (no diagram type support): Mermaid natively supports `--type` through its own syntax
- **Layout mess** (root cause of this design): Mermaid's Dagre layout replaces our broken engine for complex diagrams
