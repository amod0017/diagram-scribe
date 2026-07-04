"""Prompt construction and response parsing for LLM adapters.

All LLM adapters share the same system prompt and response parser. The LLM
chooses between two output formats based on the diagram type:

**FORMAT: mermaid** — for flowcharts, sequence diagrams, ER diagrams, class
diagrams. The LLM outputs valid Mermaid code after the header line.

**FORMAT: graph** — for architecture diagrams, mindmaps, and simple spatial
layouts. The LLM outputs a JSON object::

    {
      "nodes": [{"id": "...", "label": "...", "shape": "..."}],
      "edges": [{"from_id": "...", "to_id": "...", "label": "..."}]
    }

``parse_response()`` reads the FORMAT header and returns either a
``DiagramIR`` (graph path) or a ``MermaidIR`` (mermaid path).
"""
from __future__ import annotations
import dataclasses
import json
import re
from .models import DiagramIR, MermaidIR, Node, Edge

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
- "box": process steps, actions, tasks, services, components, classes, entities
- "diamond": decisions, conditions, branches, gateways
- "circle": start/end points, events, actors, users
- "cylinder": databases, storage systems, queues, caches
- "text": floating annotations or notes (no border; avoid connecting edges to these)

Diagram type guide — follow these conventions when a type is specified or implied:
- Flowchart: circle (start/end), box (steps), diamond (decisions), label decision edges "yes"/"no"
- Sequence diagram: circle (actors/systems), box (messages as ordered steps), label edges with the action name
- ER diagram: box (entities), cylinder (tables/stores), diamond (relationships), label edges with cardinality
- Architecture diagram: box (services), cylinder (databases), label edges with protocols or data types
- Mind map: circle (central topic), box (branches and sub-topics)
- Class diagram: box (classes), label edges with relationship type (extends, implements, uses)

Graph rules:
- Use short snake_case ids (e.g. "api_gateway", "user_db")
- Keep labels concise (4-6 words max)
- Return ONLY valid JSON — no markdown, no explanation

---
Return ONLY the FORMAT line followed by the diagram. No preamble, no explanation.
"""


def build_generate_messages(description: str) -> list[dict]:
    """Build the messages list for a generate() call.

    Args:
        description: The user's natural language diagram description.

    Returns:
        A list of message dicts in the format expected by both the
        Anthropic and OpenAI-compatible chat APIs.
    """
    return [{"role": "user", "content": f"Create a diagram for: {description}"}]


def build_refine_messages(feedback: str, current: DiagramIR) -> list[dict]:
    """Build the messages list for a refine() call.

    Includes the current diagram serialised as JSON so the LLM can
    produce an updated version that incorporates the feedback.

    Args:
        feedback: Plain English instruction for what to change.
        current: The diagram state to modify.

    Returns:
        A list of message dicts in the format expected by both the
        Anthropic and OpenAI-compatible chat APIs.
    """
    current_json = json.dumps(dataclasses.asdict(current), indent=2)
    return [
        {
            "role": "user",
            "content": (
                f"Current diagram:\n{current_json}\n\n"
                f"Feedback: {feedback}\n\n"
                "Return FORMAT: graph followed by the updated diagram as JSON."
            ),
        }
    ]


def parse_ir_response(text: str) -> DiagramIR:
    """Parse an LLM response into a DiagramIR.

    Strips Markdown code fences if the model wrapped the JSON in them,
    then parses the JSON and constructs ``Node`` and ``Edge`` objects.

    Args:
        text: Raw text from the LLM response.

    Returns:
        A ``DiagramIR`` built from the parsed JSON.

    Raises:
        ValueError: If the text is not valid JSON or missing required fields.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    text = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
    data = json.loads(text)
    nodes = [
        Node(id=n["id"], label=n["label"], shape=n["shape"])
        for n in data.get("nodes", [])
    ]
    edges = [
        Edge(from_id=e["from_id"], to_id=e["to_id"], label=e.get("label"))
        for e in data.get("edges", [])
    ]
    return DiagramIR(nodes=nodes, edges=edges)


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
        if not source:
            raise ValueError("LLM returned FORMAT: mermaid with no diagram content")
        # Strip optional code fences the LLM may wrap around the diagram.
        source = re.sub(r"^```[a-z]*\n?", "", source).rstrip("`").strip()
        first_word = source.split()[0]
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
    if not current.source:
        raise ValueError("Cannot refine a MermaidIR with empty source")
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
