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
    return [{"role": "user", "content": f"Create a diagram for: {description}"}]


def build_refine_messages(feedback: str, current: DiagramIR) -> list[dict]:
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
