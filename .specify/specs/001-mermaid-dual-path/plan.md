# Mermaid Dual-Path Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Mermaid rendering path so complex diagrams (flowcharts, sequence, ER, class) use Mermaid's layout engine instead of our hand-rolled BFS layout, while keeping the existing Excalidraw graph path for simple spatial diagrams.

**Architecture:** The LLM decides which format to use by prefixing its response with `FORMAT: mermaid` or `FORMAT: graph`. `parse_response()` strips the header and returns either a `MermaidIR` or `DiagramIR`. `DiagramScribe.draw()` routes to `MermaidAdapter` (Node.js subprocess → Excalidraw JSON) or the existing `ExcalidrawAdapter` based on the IR type. Output is always `.excalidraw`.

**Tech Stack:** Python 3.11+, Node.js ≥18, `@excalidraw/mermaid-to-excalidraw` npm package, `esbuild` for bundling, `pytest` for tests.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `src/diagram_scribe/models.py` | Modify | Add `MermaidIR` dataclass |
| `src/diagram_scribe/prompts.py` | Modify | New `SYSTEM_PROMPT`, `parse_response()`, `build_mermaid_refine_messages()` |
| `src/diagram_scribe/protocols.py` | Modify | Update `LLMAdapter` return types |
| `src/diagram_scribe/adapters/llm/openrouter.py` | Modify | Use `parse_response()` |
| `src/diagram_scribe/adapters/llm/ollama.py` | Modify | Use `parse_response()` |
| `src/diagram_scribe/adapters/llm/claude.py` | Modify | Use `parse_response()` |
| `src/diagram_scribe/core.py` | Modify | Add `output_path` param, runtime routing via `_render()` |
| `src/diagram_scribe/cli.py` | Modify | Pass `output_path` to `DiagramScribe` |
| `src/diagram_scribe/adapters/backend/mermaid.py` | Create | `MermaidAdapter` — calls Node.js bundle |
| `src/diagram_scribe/js/mermaid_to_excalidraw.bundle.js` | Create | Pre-built Node.js bundle (committed artifact) |
| `js/index.js` | Create | Source for the bundle (not shipped in Python package) |
| `js/package.json` | Create | npm deps for building the bundle |
| `js/build.js` | Create | esbuild build script |
| `tests/test_models.py` | Modify | Add `MermaidIR` tests |
| `tests/test_prompts.py` | Modify | Add `parse_response()` and `build_mermaid_refine_messages()` tests |
| `tests/test_mermaid_adapter.py` | Create | `MermaidAdapter` unit tests (mock subprocess) |
| `tests/test_core.py` | Modify | Add routing tests |
| `tests/test_integration.py` | Modify | Add Mermaid end-to-end test |

---

## Task 1: Add `MermaidIR` to `models.py`

**Files:**
- Modify: `src/diagram_scribe/models.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1.1: Write failing tests**

Add to `tests/test_models.py`:

```python
from diagram_scribe.models import MermaidIR

def test_mermaid_ir_creation():
    ir = MermaidIR(source="flowchart TD\n  A --> B", diagram_type="flowchart")
    assert ir.source == "flowchart TD\n  A --> B"
    assert ir.diagram_type == "flowchart"

def test_mermaid_ir_default_diagram_type():
    ir = MermaidIR(source="graph LR\n  A --> B")
    assert ir.diagram_type == "flowchart"
```

- [ ] **Step 1.2: Run tests to verify they fail**

```bash
/tmp/ds-dev2/bin/pytest tests/test_models.py::test_mermaid_ir_creation tests/test_models.py::test_mermaid_ir_default_diagram_type -v
```

Expected: `ImportError: cannot import name 'MermaidIR'`

- [ ] **Step 1.3: Add `MermaidIR` to `models.py`**

Append after the `DiagramIR` class in `src/diagram_scribe/models.py`:

```python
@dataclass
class MermaidIR:
    """Intermediate representation for Mermaid-rendered diagrams.

    Attributes:
        source: Raw Mermaid diagram text (e.g. ``flowchart TD\\n  A --> B``).
        diagram_type: Mermaid diagram keyword (flowchart, sequenceDiagram, etc.).
            Used for logging and debugging.
    """
    source: str
    diagram_type: str = "flowchart"
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
/tmp/ds-dev2/bin/pytest tests/test_models.py -v
```

Expected: all pass.

- [ ] **Step 1.5: Commit**

```bash
git add src/diagram_scribe/models.py tests/test_models.py
git commit -m "feat: add MermaidIR dataclass to models"
```

---

## Task 2: Add `parse_response()` and `build_mermaid_refine_messages()` to `prompts.py`

**Files:**
- Modify: `src/diagram_scribe/prompts.py`
- Modify: `tests/test_prompts.py`

- [ ] **Step 2.1: Write failing tests**

Add to `tests/test_prompts.py`:

```python
from diagram_scribe.models import MermaidIR
from diagram_scribe.prompts import parse_response, build_mermaid_refine_messages

def test_parse_response_returns_mermaid_ir_on_mermaid_format():
    text = "FORMAT: mermaid\nflowchart TD\n  A --> B"
    result = parse_response(text)
    assert isinstance(result, MermaidIR)
    assert "flowchart TD" in result.source
    assert "FORMAT: mermaid" not in result.source

def test_parse_response_returns_diagram_ir_on_graph_format():
    from diagram_scribe.models import DiagramIR
    text = 'FORMAT: graph\n{"nodes": [{"id": "a", "label": "A", "shape": "box"}], "edges": []}'
    result = parse_response(text)
    assert isinstance(result, DiagramIR)
    assert result.nodes[0].id == "a"

def test_parse_response_falls_back_to_diagram_ir_when_no_header():
    from diagram_scribe.models import DiagramIR
    text = '{"nodes": [{"id": "a", "label": "A", "shape": "box"}], "edges": []}'
    result = parse_response(text)
    assert isinstance(result, DiagramIR)

def test_parse_response_strips_think_tags_before_format_header():
    text = "<think>reasoning</think>\nFORMAT: mermaid\nflowchart TD\n  A --> B"
    result = parse_response(text)
    assert isinstance(result, MermaidIR)

def test_parse_response_detects_diagram_type_from_mermaid_source():
    text = "FORMAT: mermaid\nsequenceDiagram\n  A->>B: hello"
    result = parse_response(text)
    assert isinstance(result, MermaidIR)
    assert result.diagram_type == "sequenceDiagram"

def test_build_mermaid_refine_messages_includes_source_and_feedback():
    ir = MermaidIR(source="flowchart TD\n  A --> B", diagram_type="flowchart")
    messages = build_mermaid_refine_messages("add a C node", ir)
    assert len(messages) == 1
    assert "flowchart TD" in messages[0]["content"]
    assert "add a C node" in messages[0]["content"]
    assert "FORMAT: mermaid" in messages[0]["content"]
```

- [ ] **Step 2.2: Run tests to verify they fail**

```bash
/tmp/ds-dev2/bin/pytest tests/test_prompts.py::test_parse_response_returns_mermaid_ir_on_mermaid_format -v
```

Expected: `ImportError: cannot import name 'parse_response'`

- [ ] **Step 2.3: Implement `parse_response()` and `build_mermaid_refine_messages()` in `prompts.py`**

Add these imports at the top of `src/diagram_scribe/prompts.py` (after existing imports):

```python
from .models import DiagramIR, MermaidIR, Node, Edge
```

Replace the existing import line `from .models import DiagramIR, Node, Edge` with the line above.

Then append after `parse_ir_response()`:

```python
def parse_response(text: str) -> DiagramIR | MermaidIR:
    """Parse an LLM response that begins with a FORMAT header.

    Strips think tags, reads the first line to determine format, then
    dispatches to ``parse_ir_response`` for graph responses or constructs
    a ``MermaidIR`` for mermaid responses. Falls back to ``parse_ir_response``
    when no FORMAT header is present (backward compatibility).

    Args:
        text: Raw LLM response text.

    Returns:
        A ``MermaidIR`` or ``DiagramIR`` depending on the FORMAT header.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    lines = text.split("\n", 1)
    first_line = lines[0].strip()
    rest = lines[1].strip() if len(lines) > 1 else ""

    if first_line == "FORMAT: mermaid":
        source = rest.strip()
        first_word = source.split()[0] if source.split() else "flowchart"
        return MermaidIR(source=source, diagram_type=first_word)

    if first_line == "FORMAT: graph":
        return parse_ir_response(rest)

    # No FORMAT header — treat entire text as DiagramIR JSON (backward compat)
    return parse_ir_response(text)


def build_mermaid_refine_messages(feedback: str, current: MermaidIR) -> list[dict]:
    """Build the messages list for a refine() call on a Mermaid diagram.

    Includes the current Mermaid source so the LLM can produce an updated
    version incorporating the feedback.

    Args:
        feedback: Plain English instruction for what to change.
        current: The current Mermaid diagram state.

    Returns:
        A list of message dicts in the chat API format.
    """
    return [
        {
            "role": "user",
            "content": (
                f"Current diagram (Mermaid):\n{current.source}\n\n"
                f"Feedback: {feedback}\n\n"
                "Return the updated diagram. "
                "Remember: first line must be FORMAT: mermaid, then the Mermaid code."
            ),
        }
    ]
```

- [ ] **Step 2.4: Run tests to verify they pass**

```bash
/tmp/ds-dev2/bin/pytest tests/test_prompts.py -v
```

Expected: all pass.

- [ ] **Step 2.5: Commit**

```bash
git add src/diagram_scribe/prompts.py tests/test_prompts.py
git commit -m "feat: add parse_response() and build_mermaid_refine_messages()"
```

---

## Task 3: Update `SYSTEM_PROMPT` in `prompts.py`

**Files:**
- Modify: `src/diagram_scribe/prompts.py`

- [ ] **Step 3.1: Replace `SYSTEM_PROMPT` in `src/diagram_scribe/prompts.py`**

Replace the entire `SYSTEM_PROMPT` string with:

```python
SYSTEM_PROMPT = """\
You are a diagram generator. Given a description, choose the best output format and generate the diagram.

IMPORTANT: The FIRST line of your response MUST be one of:
  FORMAT: mermaid
  FORMAT: graph

Choose FORMAT based on the diagram type:
- flowchart, sequence diagram, ER diagram, class diagram → FORMAT: mermaid
- architecture diagram, mindmap, simple spatial layout (3-6 nodes) → FORMAT: graph
- If the description specifies a type (e.g. "[sequence diagram]"), follow it

---
If FORMAT: mermaid, output valid Mermaid code after the FORMAT line.

Mermaid diagram types:
- flowchart TD  — top-down flowchart (decisions, processes, workflows)
- sequenceDiagram — interactions between actors over time
- erDiagram — entity-relationship diagrams
- classDiagram — class/type hierarchies
- graph LR — left-to-right simple flow

Mermaid rules:
- Keep node labels short (4-6 words max)
- Use |label| on edges for decision branches (yes/no, success/failure)
- Do NOT wrap in markdown code fences

---
If FORMAT: graph, output a JSON object after the FORMAT line.

Schema:
{
  "nodes": [{"id": "string", "label": "string", "shape": "box|diamond|circle|cylinder|text"}],
  "edges": [{"from_id": "string", "to_id": "string", "label": "string or null"}]
}

Shape guide:
- "box": services, components, steps, classes, entities
- "diamond": decisions, conditions
- "circle": start/end points, actors
- "cylinder": databases, queues, storage
- "text": floating annotations (no border)

Graph rules:
- Use short snake_case ids (e.g. "api_gateway", "user_db")
- Keep labels concise (4-6 words max)
- Return ONLY valid JSON — no markdown, no explanation

---
Return ONLY the FORMAT line followed by the diagram. No preamble, no explanation.
"""
```

- [ ] **Step 3.2: Run the full test suite to confirm no regressions**

```bash
/tmp/ds-dev2/bin/pytest tests/ --ignore=tests/test_integration.py -v
```

Expected: all pass. The prompt change does not break existing tests since tests mock the LLM response.

- [ ] **Step 3.3: Commit**

```bash
git add src/diagram_scribe/prompts.py
git commit -m "feat: update SYSTEM_PROMPT for dual-path FORMAT header routing"
```

---

## Task 4: Build and commit the Node.js Mermaid-to-Excalidraw bundle

**Files:**
- Create: `js/index.js`
- Create: `js/package.json`
- Create: `js/build.js`
- Create: `src/diagram_scribe/js/mermaid_to_excalidraw.bundle.js` (built artifact)
- Create: `src/diagram_scribe/js/__init__.py` (empty, makes js/ a package data dir)

**Prerequisite:** Node.js ≥18 and npm must be installed. Verify with `node --version && npm --version`.

- [ ] **Step 4.1: Create `js/` directory and source files**

Create `js/package.json`:

```json
{
  "name": "diagram-scribe-mermaid-converter",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "build": "node build.js"
  },
  "dependencies": {
    "@excalidraw/mermaid-to-excalidraw": "^0.3.0"
  },
  "devDependencies": {
    "esbuild": "^0.21.0"
  }
}
```

Create `js/index.js`:

```javascript
import { parseMermaidToExcalidraw } from "@excalidraw/mermaid-to-excalidraw";

async function main() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const mermaidSource = Buffer.concat(chunks).toString("utf8").trim();
  if (!mermaidSource) {
    process.stderr.write("No Mermaid source provided on stdin\n");
    process.exit(1);
  }

  const { elements, files } = await parseMermaidToExcalidraw(mermaidSource);

  const output = {
    type: "excalidraw",
    version: 2,
    source: "https://excalidraw.com",
    elements,
    appState: {
      gridSize: null,
      viewBackgroundColor: "#ffffff",
    },
    files: files || {},
  };

  process.stdout.write(JSON.stringify(output));
}

main().catch((err) => {
  process.stderr.write(String(err) + "\n");
  process.exit(1);
});
```

Create `js/build.js`:

```javascript
import { build } from "esbuild";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

build({
  entryPoints: [resolve(__dirname, "index.js")],
  bundle: true,
  platform: "node",
  target: "node18",
  format: "cjs",
  outfile: resolve(__dirname, "../src/diagram_scribe/js/mermaid_to_excalidraw.bundle.js"),
  external: [],
}).catch(() => process.exit(1));
```

- [ ] **Step 4.2: Install dependencies and build the bundle**

```bash
cd /Users/amod/personalRepos/diagram-scribe/js && npm install && npm run build
```

Expected: `src/diagram_scribe/js/mermaid_to_excalidraw.bundle.js` created (will be several MB).

- [ ] **Step 4.3: Verify the bundle works**

```bash
echo 'flowchart TD\n  A[Start] --> B[End]' | node src/diagram_scribe/js/mermaid_to_excalidraw.bundle.js
```

Expected: JSON output starting with `{"type":"excalidraw","version":2,...}`.

If this fails with a DOM-related error (mermaid uses browser APIs), add a jsdom polyfill at the top of `js/index.js` before the import:

```javascript
// Polyfill required by mermaid's browser-targeted renderer
import { JSDOM } from "jsdom";
const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
global.window = dom.window;
global.document = dom.window.document;
global.navigator = dom.window.navigator;
```

Then add `"jsdom": "^24.0.0"` to `js/package.json` dependencies, run `npm install` again, and rebuild.

- [ ] **Step 4.4: Create `src/diagram_scribe/js/` package marker**

```bash
touch src/diagram_scribe/js/__init__.py
```

- [ ] **Step 4.5: Add bundle to `pyproject.toml` package data**

In `pyproject.toml`, ensure the JS bundle is included in the installed package. Find the `[tool.hatch.build.targets.wheel]` section (or add it) and include:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/diagram_scribe"]
```

Hatch includes all files in the package directory by default, so the bundle should be included automatically. Verify by checking that `src/diagram_scribe/js/` is inside `src/diagram_scribe/`.

- [ ] **Step 4.6: Add `js/node_modules/` to `.gitignore`**

```bash
echo "js/node_modules/" >> /Users/amod/personalRepos/diagram-scribe/.gitignore
```

- [ ] **Step 4.7: Commit**

```bash
git add js/ src/diagram_scribe/js/ .gitignore
git commit -m "feat: add Node.js Mermaid-to-Excalidraw bundle and build tooling"
```

---

## Task 5: Implement `MermaidAdapter`

**Files:**
- Create: `src/diagram_scribe/adapters/backend/mermaid.py`
- Create: `tests/test_mermaid_adapter.py`

- [ ] **Step 5.1: Write failing tests**

Create `tests/test_mermaid_adapter.py`:

```python
import json
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from diagram_scribe.adapters.backend.mermaid import MermaidAdapter
from diagram_scribe.models import MermaidIR


def _simple_mermaid_ir():
    return MermaidIR(source="flowchart TD\n  A[Start] --> B[End]", diagram_type="flowchart")


def _fake_excalidraw_json():
    return json.dumps({
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": [],
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    })


def test_mermaid_adapter_calls_node_subprocess(tmp_path):
    output = tmp_path / "out.excalidraw"
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = _fake_excalidraw_json()
    mock_result.stderr = ""

    with patch("diagram_scribe.adapters.backend.mermaid.subprocess.run", return_value=mock_result) as mock_run, \
         patch("diagram_scribe.adapters.backend.mermaid.webbrowser.open"):
        MermaidAdapter(output_path=str(output)).render(_simple_mermaid_ir())

    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert "node" in call_args[0][0]
    assert call_args[1]["input"] == "flowchart TD\n  A[Start] --> B[End]"


def test_mermaid_adapter_writes_excalidraw_file(tmp_path):
    output = tmp_path / "out.excalidraw"
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = _fake_excalidraw_json()
    mock_result.stderr = ""

    with patch("diagram_scribe.adapters.backend.mermaid.subprocess.run", return_value=mock_result), \
         patch("diagram_scribe.adapters.backend.mermaid.webbrowser.open"):
        MermaidAdapter(output_path=str(output)).render(_simple_mermaid_ir())

    assert output.exists()
    data = json.loads(output.read_text())
    assert data["type"] == "excalidraw"


def test_mermaid_adapter_opens_browser_on_first_render(tmp_path):
    output = tmp_path / "out.excalidraw"
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = _fake_excalidraw_json()
    mock_result.stderr = ""

    with patch("diagram_scribe.adapters.backend.mermaid.subprocess.run", return_value=mock_result), \
         patch("diagram_scribe.adapters.backend.mermaid.webbrowser.open") as mock_browser:
        adapter = MermaidAdapter(output_path=str(output))
        adapter.render(_simple_mermaid_ir())
        mock_browser.assert_called_once()
        adapter.render(_simple_mermaid_ir())
        assert mock_browser.call_count == 1


def test_mermaid_adapter_raises_when_node_missing(tmp_path):
    output = tmp_path / "out.excalidraw"
    with patch("diagram_scribe.adapters.backend.mermaid.subprocess.run",
               side_effect=FileNotFoundError("node not found")):
        with pytest.raises(RuntimeError, match="Node.js"):
            MermaidAdapter(output_path=str(output)).render(_simple_mermaid_ir())


def test_mermaid_adapter_raises_on_nonzero_exit(tmp_path):
    output = tmp_path / "out.excalidraw"
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Parse error: invalid Mermaid"

    with patch("diagram_scribe.adapters.backend.mermaid.subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="Parse error"):
            MermaidAdapter(output_path=str(output)).render(_simple_mermaid_ir())
```

- [ ] **Step 5.2: Run tests to verify they fail**

```bash
/tmp/ds-dev2/bin/pytest tests/test_mermaid_adapter.py -v
```

Expected: `ModuleNotFoundError: No module named 'diagram_scribe.adapters.backend.mermaid'`

- [ ] **Step 5.3: Implement `MermaidAdapter`**

Create `src/diagram_scribe/adapters/backend/mermaid.py`:

```python
"""Mermaid backend adapter.

Converts a ``MermaidIR`` to Excalidraw JSON by invoking a pre-built Node.js
bundle via subprocess. The bundle uses ``@excalidraw/mermaid-to-excalidraw``
to do the conversion. Node.js >=18 must be installed.

Output is written to the same ``.excalidraw`` path used by ``ExcalidrawAdapter``.
"""
from __future__ import annotations
import json
import os
import subprocess
import webbrowser
from pathlib import Path
from ...models import MermaidIR

_DEFAULT_PATH = os.path.join(os.path.expanduser("~"), "Documents", "diagram-scribe.excalidraw")
_BUNDLE = Path(__file__).parent.parent.parent / "js" / "mermaid_to_excalidraw.bundle.js"


class MermaidAdapter:
    """Backend adapter that converts Mermaid text to Excalidraw via Node.js.

    Args:
        output_path: Path to write the ``.excalidraw`` file. Defaults to
            ``~/Documents/diagram-scribe.excalidraw``.

    Raises:
        RuntimeError: If Node.js is not installed or the Mermaid source is invalid.
    """

    def __init__(self, output_path: str | None = None):
        self._output_path = output_path or _DEFAULT_PATH
        self._opened = False

    def render(self, ir: MermaidIR) -> None:
        try:
            result = subprocess.run(
                ["node", str(_BUNDLE)],
                input=ir.source,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "Node.js is required to render this diagram type. "
                "Install from https://nodejs.org (version 18 or later)."
            )

        if result.returncode != 0:
            raise RuntimeError(
                f"Mermaid conversion failed: {result.stderr.strip() or 'unknown error'}"
            )

        data = json.loads(result.stdout)
        os.makedirs(os.path.dirname(self._output_path), exist_ok=True)
        with open(self._output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        if not self._opened:
            webbrowser.open(f"file://{os.path.abspath(self._output_path)}")
            self._opened = True
        else:
            print("Diagram updated — refresh your browser tab to see changes.")
```

- [ ] **Step 5.4: Run tests to verify they pass**

```bash
/tmp/ds-dev2/bin/pytest tests/test_mermaid_adapter.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 5.5: Commit**

```bash
git add src/diagram_scribe/adapters/backend/mermaid.py tests/test_mermaid_adapter.py
git commit -m "feat: implement MermaidAdapter with Node.js subprocess"
```

---

## Task 6: Update all three LLM adapters

**Files:**
- Modify: `src/diagram_scribe/adapters/llm/openrouter.py`
- Modify: `src/diagram_scribe/adapters/llm/ollama.py`
- Modify: `src/diagram_scribe/adapters/llm/claude.py`
- Modify: `tests/test_openrouter_adapter.py`
- Modify: `tests/test_ollama_adapter.py`
- Modify: `tests/test_claude_adapter.py`

- [ ] **Step 6.1: Write failing tests for OpenRouterAdapter**

Add to `tests/test_openrouter_adapter.py`:

```python
from diagram_scribe.models import MermaidIR

def test_generate_returns_mermaid_ir_when_format_mermaid():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "FORMAT: mermaid\nflowchart TD\n  A --> B"
    )
    with patch("diagram_scribe.adapters.llm.openrouter.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        adapter = OpenRouterAdapter(api_key="test", model="test-model")
        result = adapter.generate("login flow")
    assert isinstance(result, MermaidIR)
    assert "flowchart TD" in result.source

def test_refine_passes_mermaid_ir_correctly():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "FORMAT: mermaid\nflowchart TD\n  A --> B --> C"
    )
    current = MermaidIR(source="flowchart TD\n  A --> B", diagram_type="flowchart")
    with patch("diagram_scribe.adapters.llm.openrouter.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        adapter = OpenRouterAdapter(api_key="test", model="test-model")
        result = adapter.refine("add C node", current)
    assert isinstance(result, MermaidIR)
```

- [ ] **Step 6.2: Run new tests to verify they fail**

```bash
/tmp/ds-dev2/bin/pytest tests/test_openrouter_adapter.py::test_generate_returns_mermaid_ir_when_format_mermaid -v
```

Expected: `AssertionError` (returns DiagramIR, not MermaidIR).

- [ ] **Step 6.3: Update `openrouter.py`**

Replace `src/diagram_scribe/adapters/llm/openrouter.py` with:

```python
from __future__ import annotations
from openai import OpenAI
from ...models import DiagramIR, MermaidIR
from ...prompts import (
    SYSTEM_PROMPT, build_generate_messages, build_refine_messages,
    build_mermaid_refine_messages, parse_response,
)


class OpenRouterAdapter:
    """LLM adapter that calls models via OpenRouter.

    OpenRouter provides access to hundreds of models — free and paid —
    under a single API key at https://openrouter.ai. The adapter uses the
    OpenAI-compatible chat completions endpoint.

    Free models have a ``:free`` suffix, e.g.
    ``meta-llama/llama-3.1-8b-instruct:free``. Browse models at
    https://openrouter.ai/models.

    Args:
        api_key: OpenRouter API key. Get one at https://openrouter.ai.
        model: Model ID to use.

    Example::

        from diagram_scribe.adapters.llm.openrouter import OpenRouterAdapter
        adapter = OpenRouterAdapter(api_key="sk-or-...", model="anthropic/claude-sonnet-4-6")
        ir = adapter.generate("CI/CD pipeline")
    """

    def __init__(self, api_key: str, model: str = "meta-llama/llama-3.1-8b-instruct:free"):
        self._client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        self._model = model

    def _call(self, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        )
        return response.choices[0].message.content

    def generate(self, description: str) -> DiagramIR | MermaidIR:
        return parse_response(self._call(build_generate_messages(description)))

    def refine(self, feedback: str, current: DiagramIR | MermaidIR) -> DiagramIR | MermaidIR:
        if isinstance(current, MermaidIR):
            return parse_response(self._call(build_mermaid_refine_messages(feedback, current)))
        return parse_response(self._call(build_refine_messages(feedback, current)))
```

- [ ] **Step 6.4: Update `ollama.py`**

Replace `src/diagram_scribe/adapters/llm/ollama.py` with:

```python
from __future__ import annotations
from openai import OpenAI
from ...models import DiagramIR, MermaidIR
from ...prompts import (
    SYSTEM_PROMPT, build_generate_messages, build_refine_messages,
    build_mermaid_refine_messages, parse_response,
)


class OllamaAdapter:
    """LLM adapter that calls a local Ollama server.

    Ollama (https://ollama.com) runs models on your machine with no
    internet access required after the initial model download. This
    adapter uses the OpenAI-compatible endpoint that Ollama exposes at
    ``http://localhost:11434``.

    Args:
        model: Ollama model name. Must already be pulled via ``ollama pull <model>``.
        base_url: Ollama server URL. Defaults to ``"http://localhost:11434/v1"``.

    Example::

        # terminal: ollama pull qwen2.5
        from diagram_scribe.adapters.llm.ollama import OllamaAdapter
        adapter = OllamaAdapter(model="qwen2.5")
        ir = adapter.generate("microservices architecture")
    """

    def __init__(self, model: str = "qwen2.5", base_url: str = "http://localhost:11434/v1"):
        self._client = OpenAI(base_url=base_url, api_key="ollama")
        self._model = model

    def _call(self, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        )
        return response.choices[0].message.content

    def generate(self, description: str) -> DiagramIR | MermaidIR:
        return parse_response(self._call(build_generate_messages(description)))

    def refine(self, feedback: str, current: DiagramIR | MermaidIR) -> DiagramIR | MermaidIR:
        if isinstance(current, MermaidIR):
            return parse_response(self._call(build_mermaid_refine_messages(feedback, current)))
        return parse_response(self._call(build_refine_messages(feedback, current)))
```

- [ ] **Step 6.5: Update `claude.py`**

Change the import line and both method signatures in `src/diagram_scribe/adapters/llm/claude.py`:

```python
from ...models import DiagramIR, MermaidIR
from ...prompts import (
    SYSTEM_PROMPT, build_generate_messages, build_refine_messages,
    build_mermaid_refine_messages, parse_response,
)
```

Replace `generate` and `refine`:

```python
    def generate(self, description: str) -> DiagramIR | MermaidIR:
        return parse_response(self._call(build_generate_messages(description)))

    def refine(self, feedback: str, current: DiagramIR | MermaidIR) -> DiagramIR | MermaidIR:
        if isinstance(current, MermaidIR):
            return parse_response(self._call(build_mermaid_refine_messages(feedback, current)))
        return parse_response(self._call(build_refine_messages(feedback, current)))
```

- [ ] **Step 6.6: Add matching tests for Ollama and Claude adapters**

Add to `tests/test_ollama_adapter.py`:

```python
from diagram_scribe.models import MermaidIR

def test_generate_returns_mermaid_ir_when_format_mermaid():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "FORMAT: mermaid\nflowchart TD\n  A --> B"
    with patch("diagram_scribe.adapters.llm.ollama.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        adapter = OllamaAdapter(model="qwen2.5")
        result = adapter.generate("login flow")
    assert isinstance(result, MermaidIR)
```

Add to `tests/test_claude_adapter.py`:

```python
from diagram_scribe.models import MermaidIR

def test_generate_returns_mermaid_ir_when_format_mermaid():
    mock_response = MagicMock()
    mock_response.content[0].text = "FORMAT: mermaid\nflowchart TD\n  A --> B"
    with patch("diagram_scribe.adapters.llm.claude.anthropic.Anthropic") as mock_anthropic:
        mock_anthropic.return_value.messages.create.return_value = mock_response
        from diagram_scribe.adapters.llm.claude import ClaudeAdapter
        adapter = ClaudeAdapter(api_key="test")
        result = adapter.generate("login flow")
    assert isinstance(result, MermaidIR)
```

- [ ] **Step 6.7: Run all adapter tests**

```bash
/tmp/ds-dev2/bin/pytest tests/test_openrouter_adapter.py tests/test_ollama_adapter.py tests/test_claude_adapter.py -v
```

Expected: all pass.

- [ ] **Step 6.8: Commit**

```bash
git add src/diagram_scribe/adapters/llm/ tests/test_openrouter_adapter.py tests/test_ollama_adapter.py tests/test_claude_adapter.py
git commit -m "feat: update LLM adapters to return DiagramIR | MermaidIR via parse_response()"
```

---

## Task 7: Update `protocols.py`

**Files:**
- Modify: `src/diagram_scribe/protocols.py`

- [ ] **Step 7.1: Update `LLMAdapter` return types**

Replace `src/diagram_scribe/protocols.py` with:

```python
from typing import Protocol
from .models import DiagramIR, MermaidIR


class LLMAdapter(Protocol):
    """Interface for LLM backends.

    Implementations translate natural language into a ``DiagramIR`` or
    ``MermaidIR`` depending on the diagram type. The three built-in
    implementations are :class:`ClaudeAdapter`, :class:`OpenRouterAdapter`,
    and :class:`OllamaAdapter`.
    """

    def generate(self, description: str) -> DiagramIR | MermaidIR:
        """Convert a natural language description into a diagram.

        Args:
            description: Plain English description of the diagram to create.

        Returns:
            A ``DiagramIR`` for graph-path diagrams or a ``MermaidIR`` for
            Mermaid-path diagrams.
        """
        ...

    def refine(self, feedback: str, current: DiagramIR | MermaidIR) -> DiagramIR | MermaidIR:
        """Update an existing diagram based on user feedback.

        Args:
            feedback: Plain English instruction describing what to change.
            current: The current diagram state (either a ``DiagramIR`` or ``MermaidIR``).

        Returns:
            An updated diagram of the same type as ``current``.
        """
        ...


class BackendAdapter(Protocol):
    """Interface for diagram rendering backends.

    Implementations translate a diagram IR into a concrete file format.
    """

    def render(self, ir: DiagramIR) -> None:
        """Render a diagram from its intermediate representation.

        Args:
            ir: The diagram to render.
        """
        ...
```

- [ ] **Step 7.2: Run the full test suite**

```bash
/tmp/ds-dev2/bin/pytest tests/ --ignore=tests/test_integration.py -v
```

Expected: all pass.

- [ ] **Step 7.3: Commit**

```bash
git add src/diagram_scribe/protocols.py
git commit -m "feat: update LLMAdapter protocol to return DiagramIR | MermaidIR"
```

---

## Task 8: Update `core.py` with runtime routing

**Files:**
- Modify: `src/diagram_scribe/core.py`
- Modify: `tests/test_core.py`

- [ ] **Step 8.1: Write failing tests**

Add to `tests/test_core.py`:

```python
from diagram_scribe.models import MermaidIR

def test_draw_routes_mermaid_ir_to_mermaid_adapter():
    mermaid_ir = MermaidIR(source="flowchart TD\n  A --> B", diagram_type="flowchart")
    mock_llm = MagicMock()
    mock_llm.generate.return_value = mermaid_ir
    mock_mermaid_backend = MagicMock()

    ds = DiagramScribe(llm=mock_llm, backend=MagicMock())
    # Inject mock mermaid backend
    ds._mermaid_backend = mock_mermaid_backend

    result = ds.draw("login flow")
    mock_mermaid_backend.render.assert_called_once_with(mermaid_ir)
    assert isinstance(result, MermaidIR)

def test_draw_routes_diagram_ir_to_excalidraw_backend():
    from diagram_scribe.models import DiagramIR, Node
    diagram_ir = DiagramIR(nodes=[Node("a", "A", "box")], edges=[])
    mock_llm = MagicMock()
    mock_llm.generate.return_value = diagram_ir
    mock_backend = MagicMock()

    ds = DiagramScribe(llm=mock_llm, backend=mock_backend)
    result = ds.draw("simple flow")
    mock_backend.render.assert_called_once_with(diagram_ir)
    assert isinstance(result, DiagramIR)

def test_refine_routes_mermaid_ir_correctly():
    initial_ir = MermaidIR(source="flowchart TD\n  A --> B", diagram_type="flowchart")
    refined_ir = MermaidIR(source="flowchart TD\n  A --> B --> C", diagram_type="flowchart")
    mock_llm = MagicMock()
    mock_llm.generate.return_value = initial_ir
    mock_llm.refine.return_value = refined_ir
    mock_mermaid_backend = MagicMock()

    ds = DiagramScribe(llm=mock_llm, backend=MagicMock())
    ds._mermaid_backend = mock_mermaid_backend
    ds.draw("flow")
    result = ds.refine("add C")

    assert mock_mermaid_backend.render.call_count == 2
    assert isinstance(result, MermaidIR)

def test_diagram_scribe_accepts_output_path():
    ds = DiagramScribe(llm=MagicMock(), backend=MagicMock(), output_path="/tmp/test.excalidraw")
    assert ds._output_path == "/tmp/test.excalidraw"
```

- [ ] **Step 8.2: Run tests to verify they fail**

```bash
/tmp/ds-dev2/bin/pytest tests/test_core.py::test_draw_routes_mermaid_ir_to_mermaid_adapter -v
```

Expected: `AttributeError: 'DiagramScribe' object has no attribute '_mermaid_backend'`

- [ ] **Step 8.3: Update `core.py`**

Replace `src/diagram_scribe/core.py` with:

```python
"""DiagramScribe core — wires LLM and backend adapters together.

This is the main entry point for library users. Instantiate
:class:`DiagramScribe`, call :meth:`DiagramScribe.draw` with a description,
then call :meth:`DiagramScribe.refine` as many times as needed.

Default adapters are selected from environment variables when no
explicit adapter is passed. See :mod:`diagram_scribe.cli` for how the
CLI picks adapters.
"""
from __future__ import annotations
from .models import DiagramIR, MermaidIR
from .protocols import LLMAdapter, BackendAdapter


class DiagramScribe:
    """Orchestrates diagram generation and refinement.

    Routes LLM output to the appropriate backend: ``ExcalidrawAdapter`` for
    ``DiagramIR`` (simple spatial diagrams) or ``MermaidAdapter`` for
    ``MermaidIR`` (flowcharts, sequence diagrams, ER diagrams, class diagrams).

    Args:
        llm: An LLM adapter. Defaults to ``OpenRouterAdapter`` using env vars.
        backend: A backend adapter for the graph path. Defaults to
            ``ExcalidrawAdapter``. Used directly in tests to inject mocks.
        output_path: Output ``.excalidraw`` file path. Passed to both
            ``ExcalidrawAdapter`` and ``MermaidAdapter``.

    Example::

        from diagram_scribe import DiagramScribe

        ds = DiagramScribe()
        ds.draw("Two services: API gateway routes to user service.")
        ds.refine("add a database behind the user service")
    """

    def __init__(
        self,
        llm: LLMAdapter | None = None,
        backend: BackendAdapter | None = None,
        output_path: str | None = None,
    ):
        self._llm = llm or self._default_llm()
        self._output_path = output_path
        self._excalidraw_backend = backend or self._default_backend(output_path)
        self._mermaid_backend: object | None = None
        self._current_ir: DiagramIR | MermaidIR | None = None

    @staticmethod
    def _default_llm() -> LLMAdapter:
        import os
        from .adapters.llm.openrouter import OpenRouterAdapter
        return OpenRouterAdapter(
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            model=os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free"),
        )

    @staticmethod
    def _default_backend(output_path: str | None = None) -> BackendAdapter:
        from .adapters.backend.excalidraw import ExcalidrawAdapter
        return ExcalidrawAdapter(output_path=output_path)

    def _get_mermaid_backend(self) -> object:
        if self._mermaid_backend is None:
            from .adapters.backend.mermaid import MermaidAdapter
            self._mermaid_backend = MermaidAdapter(output_path=self._output_path)
        return self._mermaid_backend

    def _render(self, ir: DiagramIR | MermaidIR) -> None:
        if isinstance(ir, MermaidIR):
            self._get_mermaid_backend().render(ir)
        else:
            self._excalidraw_backend.render(ir)

    def draw(self, description: str) -> DiagramIR | MermaidIR:
        """Generate a new diagram from a natural language description.

        The LLM decides the output format (Mermaid or graph). The appropriate
        backend renders and saves the result as a ``.excalidraw`` file.

        Args:
            description: Plain English description of the diagram to create.

        Returns:
            The generated ``DiagramIR`` or ``MermaidIR``.
        """
        self._current_ir = self._llm.generate(description)
        self._render(self._current_ir)
        return self._current_ir

    def refine(self, feedback: str) -> DiagramIR | MermaidIR:
        """Update the current diagram based on feedback.

        Must be called after :meth:`draw`. The LLM receives the current
        diagram state and the feedback, returns an updated IR of the same type,
        and the backend re-renders it.

        Args:
            feedback: Plain English instruction describing what to change.

        Returns:
            The updated ``DiagramIR`` or ``MermaidIR``.

        Raises:
            RuntimeError: If called before :meth:`draw`.
        """
        if self._current_ir is None:
            raise RuntimeError("Call draw() before refine()")
        self._current_ir = self._llm.refine(feedback, self._current_ir)
        self._render(self._current_ir)
        return self._current_ir
```

- [ ] **Step 8.4: Run all core tests**

```bash
/tmp/ds-dev2/bin/pytest tests/test_core.py -v
```

Expected: all pass.

- [ ] **Step 8.5: Commit**

```bash
git add src/diagram_scribe/core.py tests/test_core.py
git commit -m "feat: add output_path param and MermaidIR routing to DiagramScribe"
```

---

## Task 9: Update `cli.py`

**Files:**
- Modify: `src/diagram_scribe/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 9.1: Update `main()` in `cli.py`**

In `src/diagram_scribe/cli.py`, find the block that constructs `ExcalidrawAdapter` and `DiagramScribe`:

```python
    output_path = args.output or os.getenv("DIAGRAM_SCRIBE_OUTPUT")
    backend = ExcalidrawAdapter(output_path=output_path)
    ds = DiagramScribe(llm=llm, backend=backend)
```

Replace with:

```python
    output_path = args.output or os.getenv("DIAGRAM_SCRIBE_OUTPUT")
    backend = ExcalidrawAdapter(output_path=output_path)
    ds = DiagramScribe(llm=llm, backend=backend, output_path=output_path)
```

Then update the path display line:

```python
    print(f"[diagram saved to {backend._output_path}]\n")
```

This line remains correct — `backend` is still the local `ExcalidrawAdapter` which has the right `_output_path`.

- [ ] **Step 9.2: Run the full test suite**

```bash
/tmp/ds-dev2/bin/pytest tests/ --ignore=tests/test_integration.py -v
```

Expected: all pass with no regressions.

- [ ] **Step 9.3: Commit**

```bash
git add src/diagram_scribe/cli.py
git commit -m "feat: pass output_path to DiagramScribe in CLI"
```

---

## Task 10: End-to-end integration test

**Files:**
- Modify: `tests/test_integration.py`

- [ ] **Step 10.1: Add Mermaid integration test**

Add to `tests/test_integration.py`:

```python
import json
import os
import pytest

@pytest.mark.integration
def test_mermaid_path_generates_valid_excalidraw(tmp_path):
    """Real LLM + real Node.js — verifies the full Mermaid path end to end."""
    pytest.importorskip("subprocess")  # always available, just documents intent
    output = tmp_path / "test.excalidraw"

    from diagram_scribe.core import DiagramScribe

    ds = DiagramScribe(output_path=str(output))
    result = ds.draw("[flowchart diagram] user login with email and password")

    from diagram_scribe.models import MermaidIR
    assert isinstance(result, MermaidIR), f"Expected MermaidIR, got {type(result)}"
    assert output.exists(), "Output file was not written"
    data = json.loads(output.read_text())
    assert data["type"] == "excalidraw"
    assert len(data["elements"]) > 0
```

- [ ] **Step 10.2: Run the integration test**

Requires: `OPENROUTER_API_KEY` set in environment and Node.js ≥18 installed.

```bash
/tmp/ds-dev2/bin/pytest tests/test_integration.py::test_mermaid_path_generates_valid_excalidraw -v -m integration
```

Expected: PASS with a valid `.excalidraw` file written to `tmp_path`.

- [ ] **Step 10.3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add Mermaid end-to-end integration test"
```

---

## Task 11: Open PR and merge

- [ ] **Step 11.1: Run the complete unit test suite one final time**

```bash
/tmp/ds-dev2/bin/pytest tests/ --ignore=tests/test_integration.py -v
```

Expected: all pass.

- [ ] **Step 11.2: Push and open PR**

```bash
git push -u origin <current-branch>
gh pr create \
  --title "feat: Mermaid dual-path rendering — LLM chooses format, Node.js converts to Excalidraw" \
  --body "Closes the layout mess. Implements spec .specify/specs/001-mermaid-dual-path/spec.md"
```

- [ ] **Step 11.3: Merge**

```bash
gh pr merge --squash --auto
```
