"""Prompt construction and response parsing for LLM adapters.

All LLM adapters share the same prompts and the same JSON schema. This
module keeps that logic in one place so changing the prompt affects every
adapter at once.

The LLM is always asked to return a JSON object with this shape::

    {
      "nodes": [{"id": "...", "label": "...", "shape": "..."}],
      "edges": [{"from_id": "...", "to_id": "...", "label": "..."}]
    }

``shape`` must be one of "box", "diamond", "circle", "cylinder".
``label`` on edges is optional.
"""
from __future__ import annotations
import dataclasses
import json
import re
from .models import DiagramIR, Node, Edge

SYSTEM_PROMPT = """\
You are a diagram generator. Given a description, return a JSON object.

Schema:
{
  "nodes": [{"id": "string", "label": "string", "shape": "box|diamond|circle|cylinder"}],
  "edges": [{"from_id": "string", "to_id": "string", "label": "string or null"}]
}

Shape guide:
- "box": process steps, actions, tasks
- "diamond": decisions, conditions, branches
- "circle": start and end points
- "cylinder": databases, storage, queues

Rules:
- Use short snake_case ids (e.g. "validate_token", "deploy_staging")
- Label edges on decisions (e.g. "yes", "no", "success", "failure")
- Return ONLY valid JSON. No markdown, no explanation.
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
                "Return the updated diagram as JSON."
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
