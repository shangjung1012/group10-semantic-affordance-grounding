from __future__ import annotations

from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace, RDF, RDFS


ROOT = Path(__file__).resolve().parents[1]

COURSE_ONTOLOGY = ROOT / "ontology/imports/course-affordance.ttl"
GROUP_ONTOLOGY = ROOT / "ontology/group-ontology.ttl"
SHAPES = ROOT / "ontology/shapes.ttl"
VALIDATION_OUTPUT = ROOT / "results/shacl_validation_output.txt"

CAP = Namespace("https://hcis.io/ontology/aicapstone/2026/")
G10 = Namespace("https://hcis.io/ontology/aicapstone/2026/group10/")


def load_turtle(path: Path) -> Graph:
    graph = Graph()
    graph.bind("cap", CAP)
    graph.bind("g10", G10)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.parse(path, format="turtle")
    return graph


def load_data_graph() -> Graph:
    """Group instances plus the course vocabulary, so that subclass
    types (e.g. cap:Cup -> cap:PhysicalObject) can be resolved by RDFS
    inference during validation."""
    graph = load_turtle(GROUP_ONTOLOGY)
    graph.parse(COURSE_ONTOLOGY, format="turtle")
    return graph


def run_validation() -> tuple[bool, str]:
    data_graph = load_data_graph()
    shapes_graph = load_turtle(SHAPES)
    ontology_graph = load_turtle(COURSE_ONTOLOGY)

    conforms, _results_graph, results_text = validate(
        data_graph,
        shacl_graph=shapes_graph,
        ont_graph=ontology_graph,
        inference="rdfs",
        advanced=True,
    )
    return conforms, results_text


def main() -> None:
    conforms, results_text = run_validation()

    VALIDATION_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_OUTPUT.write_text(results_text)

    status = "PASS" if conforms else "FAIL"
    print(f"SHACL validation: {status} (Conforms: {conforms})")
    print(f"Wrote {VALIDATION_OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
