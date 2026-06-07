from __future__ import annotations

from pathlib import Path
from typing import Iterable

from owlrl import DeductiveClosure, OWLRL_Semantics
from rdflib import Graph, Namespace, RDF, RDFS, URIRef
from rdflib.compare import to_canonical_graph
from rdflib.query import ResultRow


ROOT = Path(__file__).resolve().parents[1]

COURSE_ONTOLOGY = ROOT / "ontology/imports/course-affordance.ttl"
COURSE_ALIGNMENT = ROOT / "ontology/imports/course-alignment.ttl"
GROUP_ONTOLOGY = ROOT / "ontology/group-ontology.ttl"
INFERRED_RESULTS = ROOT / "ontology/inferred-results.ttl"
QUERIES = {
    ROOT / "queries/graspable_objects.rq": ROOT / "results/graspable_objects_output.txt",
    ROOT / "queries/task_objects.rq": ROOT / "results/task_objects_output.txt",
    ROOT / "queries/non_graspable_task_objects.rq": (
        ROOT / "results/non_graspable_task_objects_output.txt"
    ),
    ROOT / "queries/object_affordance_summary.rq": (
        ROOT / "results/object_affordance_summary_output.txt"
    ),
}

CAP = Namespace("https://hcis.io/ontology/aicapstone/2026/")
G10 = Namespace("https://hcis.io/ontology/aicapstone/2026/group10/")
LOCAL_COURSE_IMPORT = URIRef("imports/course-affordance.ttl")


def load_graph() -> Graph:
    graph = Graph()
    graph.bind("cap", CAP)
    graph.bind("g10", G10)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.parse(COURSE_ONTOLOGY, format="turtle")
    graph.parse(COURSE_ALIGNMENT, format="turtle")
    graph.parse(GROUP_ONTOLOGY, format="turtle")
    return graph


def has_type_or_subclass(graph: Graph, individual: URIRef, target_class: URIRef) -> bool:
    for class_iri in graph.objects(individual, RDF.type):
        if class_iri == target_class or (class_iri, RDFS.subClassOf, target_class) in graph:
            return True
    return False


def materialize_graspable_objects(graph: Graph) -> int:
    inferred_count = 0
    for obj in set(graph.subjects(RDF.type, CAP.PhysicalObject)):
        for affordance in graph.objects(obj, CAP.hasAffordance):
            if has_type_or_subclass(graph, affordance, CAP.GraspingAffordance):
                triple = (obj, RDF.type, CAP.GraspableObject)
                if triple not in graph:
                    graph.add(triple)
                    inferred_count += 1
                break
    return inferred_count


def run_reasoning(graph: Graph) -> Graph:
    DeductiveClosure(
        OWLRL_Semantics,
        rdfs_closure=True,
        axiomatic_triples=False,
        datatype_axioms=False,
    ).expand(graph)
    materialize_graspable_objects(graph)
    return graph


def compact_value(graph: Graph, value: object) -> str:
    if isinstance(value, URIRef):
        return graph.namespace_manager.normalizeUri(value)
    return str(value)


def format_rows(graph: Graph, rows: Iterable[ResultRow], variables: list[str]) -> str:
    rows = list(rows)
    widths = {
        variable: max(
            len(variable),
            *(len(compact_value(graph, row.get(variable, ""))) for row in rows),
        )
        for variable in variables
    }

    header = " | ".join(variable.ljust(widths[variable]) for variable in variables)
    divider = "-+-".join("-" * widths[variable] for variable in variables)
    lines = [header, divider]

    for row in rows:
        lines.append(
            " | ".join(
                compact_value(graph, row.get(variable, "")).ljust(widths[variable])
                for variable in variables
            )
        )

    return "\n".join(lines) + "\n"


def write_query_outputs(graph: Graph) -> None:
    for query_path, output_path in QUERIES.items():
        query = query_path.read_text()
        result = graph.query(query)
        variables = [str(variable) for variable in result.vars]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(format_rows(graph, result, variables))


def serialize_inferred_graph(graph: Graph) -> None:
    canonical_graph = Graph()
    for prefix, namespace in graph.namespaces():
        canonical_graph.bind(prefix, namespace)
    for subject, predicate, object_ in to_canonical_graph(graph):
        normalized_subject = (
            LOCAL_COURSE_IMPORT if subject == URIRef(COURSE_ONTOLOGY.as_uri()) else subject
        )
        normalized_object = (
            LOCAL_COURSE_IMPORT if object_ == URIRef(COURSE_ONTOLOGY.as_uri()) else object_
        )
        canonical_graph.add((normalized_subject, predicate, normalized_object))
    canonical_graph.serialize(destination=INFERRED_RESULTS, format="turtle")


def main() -> None:
    graph = run_reasoning(load_graph())
    INFERRED_RESULTS.parent.mkdir(parents=True, exist_ok=True)
    serialize_inferred_graph(graph)
    write_query_outputs(graph)
    print(f"Wrote {INFERRED_RESULTS.relative_to(ROOT)}")
    for output_path in QUERIES.values():
        print(f"Wrote {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
