from diagram_scribe.models import Node, Edge, DiagramIR, MermaidIR


def test_node_creation():
    node = Node(id="start", label="Start", shape="circle")
    assert node.id == "start"
    assert node.label == "Start"
    assert node.shape == "circle"


def test_edge_with_label():
    edge = Edge(from_id="a", to_id="b", label="yes")
    assert edge.from_id == "a"
    assert edge.to_id == "b"
    assert edge.label == "yes"


def test_edge_without_label_defaults_to_none():
    edge = Edge(from_id="a", to_id="b")
    assert edge.label is None


def test_diagram_ir_holds_nodes_and_edges():
    nodes = [Node("a", "A", "box"), Node("b", "B", "box")]
    edges = [Edge("a", "b")]
    ir = DiagramIR(nodes=nodes, edges=edges)
    assert len(ir.nodes) == 2
    assert len(ir.edges) == 1


def test_diagram_ir_empty_by_default():
    ir = DiagramIR()
    assert ir.nodes == []
    assert ir.edges == []


def test_mermaid_ir_creation():
    ir = MermaidIR(source="flowchart TD\n  A --> B", diagram_type="flowchart")
    assert ir.source == "flowchart TD\n  A --> B"
    assert ir.diagram_type == "flowchart"


def test_mermaid_ir_default_diagram_type():
    ir = MermaidIR(source="graph LR\n  A --> B")
    assert ir.diagram_type == "flowchart"
