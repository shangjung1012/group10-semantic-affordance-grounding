from pathlib import Path
import subprocess
import sys

from pyshacl import validate
from rdflib import Graph, Namespace, RDF


ROOT = Path(__file__).resolve().parents[1]
CAP = Namespace("https://hcis.io/ontology/aicapstone/2026/")
G10 = Namespace("https://hcis.io/ontology/aicapstone/2026/group10/")

COURSE_ONTOLOGY = ROOT / "ontology/imports/course-affordance.ttl"
GROUP_ONTOLOGY = ROOT / "ontology/group-ontology.ttl"
SHAPES = ROOT / "ontology/shapes.ttl"


def parse_turtle(path: Path) -> Graph:
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def build_data_graph() -> Graph:
    graph = parse_turtle(GROUP_ONTOLOGY)
    graph.parse(COURSE_ONTOLOGY, format="turtle")
    return graph


def validate_graph(data_graph: Graph):
    return validate(
        data_graph,
        shacl_graph=parse_turtle(SHAPES),
        ont_graph=parse_turtle(COURSE_ONTOLOGY),
        inference="rdfs",
        advanced=True,
    )


def test_shapes_file_parses_as_turtle() -> None:
    parse_turtle(SHAPES)


def test_baseline_graph_conforms() -> None:
    conforms, _results_graph, _text = validate_graph(build_data_graph())
    assert conforms is True


def test_validation_script_writes_output() -> None:
    subprocess.run(
        [sys.executable, "src/run_validation.py"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    output = (ROOT / "results/shacl_validation_output.txt").read_text()
    assert "Conforms" in output


def test_missing_label_violates_shape() -> None:
    """Removing a required cap:hasObjectLabel must make the graph fail,
    proving the constraint is actually enforced rather than vacuous."""
    data_graph = build_data_graph()
    data_graph.remove((G10.blueCup01, CAP.hasObjectLabel, None))

    conforms, _results_graph, _text = validate_graph(data_graph)
    assert conforms is False
