"""Ontology analysis and visualization report generator.

Produces a Markdown report with:
  1. Ontology metrics (triple, class, property, and individual counts).
  2. Affordance coverage matrix (object × affordance).
  3. Graspability reasoning explanation per object.
  4. Mermaid class hierarchy diagram.

This module uses programmatic RDFLib graph traversal.  It does **not**
rely on the SPARQL query files shipped under ``queries/``.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

from owlrl import DeductiveClosure, OWLRL_Semantics
from rdflib import Graph, Namespace, OWL, RDF, RDFS, URIRef
from rdflib.term import Node


ROOT = Path(__file__).resolve().parents[1]

COURSE_ONTOLOGY = ROOT / "ontology/imports/course-affordance.ttl"
COURSE_ALIGNMENT = ROOT / "ontology/imports/course-alignment.ttl"
GROUP_ONTOLOGY = ROOT / "ontology/group-ontology.ttl"
INFERRED_RESULTS = ROOT / "ontology/inferred-results.ttl"
REPORT_OUTPUT = ROOT / "results/analysis_report.md"

CAP = Namespace("https://hcis.io/ontology/aicapstone/2026/")
G10 = Namespace("https://hcis.io/ontology/aicapstone/2026/group10/")


# ---------------------------------------------------------------------------
# Graph loading helpers
# ---------------------------------------------------------------------------

def load_source_graph() -> Graph:
    """Load the un-inferred source ontology graph."""
    graph = Graph()
    graph.bind("cap", CAP)
    graph.bind("g10", G10)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.parse(COURSE_ONTOLOGY, format="turtle")
    graph.parse(COURSE_ALIGNMENT, format="turtle")
    graph.parse(GROUP_ONTOLOGY, format="turtle")
    return graph


def load_inferred_graph() -> Graph:
    """Load the inferred-results graph produced by ``run_reasoning.py``."""
    graph = Graph()
    graph.bind("cap", CAP)
    graph.bind("g10", G10)
    graph.parse(INFERRED_RESULTS, format="turtle")
    return graph


# ---------------------------------------------------------------------------
# 1. Ontology Metrics
# ---------------------------------------------------------------------------

def _is_g10(uri: Node) -> bool:
    return isinstance(uri, URIRef) and str(uri).startswith(str(G10))


def _is_cap(uri: Node) -> bool:
    return isinstance(uri, URIRef) and str(uri).startswith(str(CAP))


def _short(uri: Node) -> str:
    """Return a compact prefixed name for display."""
    s = str(uri)
    if s.startswith(str(G10)):
        return f"g10:{s[len(str(G10)):]}"
    if s.startswith(str(CAP)):
        return f"cap:{s[len(str(CAP)):]}"
    return s


def compute_metrics(source: Graph, inferred: Graph) -> dict:
    """Return a dictionary of ontology-level metrics."""
    classes = set(source.subjects(RDF.type, OWL.Class)) | set(
        source.subjects(RDF.type, RDFS.Class)
    )
    obj_props = set(source.subjects(RDF.type, OWL.ObjectProperty))
    dt_props = set(source.subjects(RDF.type, OWL.DatatypeProperty))

    # Individuals: g10: namespace typed instances
    g10_individuals = {
        s for s in source.subjects(RDF.type, None) if _is_g10(s)
    }
    cap_classes = {c for c in classes if _is_cap(c)}
    g10_classes = {c for c in classes if _is_g10(c)}

    return {
        "source_triples": len(source),
        "inferred_triples": len(inferred),
        "class_count": len(classes),
        "cap_class_count": len(cap_classes),
        "g10_class_count": len(g10_classes),
        "object_property_count": len(obj_props),
        "datatype_property_count": len(dt_props),
        "g10_individual_count": len(g10_individuals),
    }


# ---------------------------------------------------------------------------
# 2. Affordance Coverage Matrix
# ---------------------------------------------------------------------------

AFFORDANCE_TYPES: list[tuple[str, URIRef]] = [
    ("Grasping", CAP.GraspingAffordance),
    ("Support", CAP.SupportAffordance),
    ("Containment", CAP.ContainmentAffordance),
    ("Stackability", CAP.StackabilityAffordance),
]


def _has_type_or_subclass(graph: Graph, individual: URIRef, target: URIRef) -> bool:
    for cls in graph.objects(individual, RDF.type):
        if cls == target or (cls, RDFS.subClassOf, target) in graph:
            return True
    return False


def compute_affordance_matrix(
    source: Graph,
) -> list[dict]:
    """For each g10: PhysicalObject instance, check which affordance types it has."""
    g10_objects = sorted(
        {
            s
            for s in source.subjects(RDF.type, None)
            if _is_g10(s)
            and _has_type_or_subclass(source, s, CAP.PhysicalObject)
        },
        key=str,
    )
    rows = []
    for obj in g10_objects:
        affordances = set(source.objects(obj, CAP.hasAffordance))
        row: dict = {"object": _short(obj)}
        for label, aff_class in AFFORDANCE_TYPES:
            row[label] = any(
                _has_type_or_subclass(source, aff, aff_class) for aff in affordances
            )
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# 3. Graspability Reasoning Explanation
# ---------------------------------------------------------------------------

def compute_graspability_explanations(
    source: Graph, inferred: Graph
) -> list[dict]:
    """For each g10: PhysicalObject, explain the graspability inference."""
    g10_objects = sorted(
        {
            s
            for s in source.subjects(RDF.type, None)
            if _is_g10(s)
            and _has_type_or_subclass(source, s, CAP.PhysicalObject)
        },
        key=str,
    )

    explanations: list[dict] = []
    for obj in g10_objects:
        affordances = list(source.objects(obj, CAP.hasAffordance))
        has_grasping = any(
            _has_type_or_subclass(source, aff, CAP.GraspingAffordance)
            for aff in affordances
        )

        is_graspable = (obj, RDF.type, CAP.GraspableObject) in inferred

        aff_names = []
        for aff in affordances:
            for label, aff_class in AFFORDANCE_TYPES:
                if _has_type_or_subclass(source, aff, aff_class):
                    aff_names.append(label)

        obj_types = [
            _short(t)
            for t in source.objects(obj, RDF.type)
            if _is_cap(t) and t != CAP.PhysicalObject
        ]

        explanations.append(
            {
                "object": _short(obj),
                "types": obj_types,
                "affordances": aff_names,
                "has_grasping_affordance": has_grasping,
                "inferred_graspable": is_graspable,
            }
        )
    return explanations


# ---------------------------------------------------------------------------
# 4. Class Hierarchy Mermaid Diagram
# ---------------------------------------------------------------------------

def build_class_hierarchy(source: Graph) -> list[tuple[str, str]]:
    """Extract (child, parent) pairs from rdfs:subClassOf for cap: classes."""
    edges: list[tuple[str, str]] = []
    seen = set()
    for child, parent in source.subject_objects(RDFS.subClassOf):
        if not isinstance(child, URIRef) or not isinstance(parent, URIRef):
            continue
        if not (_is_cap(child) or _is_g10(child)):
            continue
        if not (_is_cap(parent) or _is_g10(parent)):
            continue
        c = _short(child)
        p = _short(parent)
        pair = (c, p)
        if pair not in seen:
            seen.add(pair)
            edges.append(pair)
    return sorted(edges)


def render_mermaid_hierarchy(edges: list[tuple[str, str]]) -> str:
    """Return a Mermaid graph TD block for the class hierarchy."""
    lines = ["graph TD"]
    for child, parent in edges:
        # Sanitize node ids for Mermaid (replace : with _)
        child_id = child.replace(":", "_")
        parent_id = parent.replace(":", "_")
        lines.append(f'    {parent_id}["{parent}"] --> {child_id}["{child}"]')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    metrics: dict,
    matrix: list[dict],
    explanations: list[dict],
    mermaid: str,
) -> str:
    """Compose the full Markdown analysis report."""
    sections: list[str] = []

    # Title
    sections.append("# Ontology Analysis Report\n")
    sections.append(
        "This report is auto-generated by `src/run_analysis.py`. "
        "It provides quantitative metrics, affordance coverage analysis, "
        "graspability reasoning explanations, and a class hierarchy diagram "
        "for the Group 10 Semantic Affordance Grounding ontology.\n"
    )

    # 1. Metrics
    sections.append("## 1. Ontology Metrics\n")
    sections.append("| Metric | Value |")
    sections.append("| --- | --- |")
    metric_labels = [
        ("Source triples (before reasoning)", "source_triples"),
        ("Inferred triples (after reasoning)", "inferred_triples"),
        ("OWL/RDFS classes", "class_count"),
        ("Classes in cap: namespace", "cap_class_count"),
        ("Classes in g10: namespace", "g10_class_count"),
        ("Object properties", "object_property_count"),
        ("Datatype properties", "datatype_property_count"),
        ("Group 10 individuals", "g10_individual_count"),
    ]
    for label, key in metric_labels:
        sections.append(f"| {label} | {metrics[key]} |")
    sections.append("")

    # 2. Affordance Coverage Matrix
    sections.append("## 2. Affordance Coverage Matrix\n")
    aff_labels = [label for label, _ in AFFORDANCE_TYPES]
    header = "| Object | " + " | ".join(aff_labels) + " |"
    divider = "| --- | " + " | ".join("---" for _ in aff_labels) + " |"
    sections.append(header)
    sections.append(divider)
    for row in matrix:
        cells = [row["object"]]
        for label in aff_labels:
            cells.append("✓" if row[label] else "—")
        sections.append("| " + " | ".join(cells) + " |")
    sections.append("")

    # 3. Graspability Reasoning Explanation
    sections.append("## 3. Graspability Reasoning Explanation\n")
    sections.append(
        "For each Group 10 physical object, the table below shows the "
        "inference chain that determines graspability.\n"
    )
    sections.append(
        "| Object | Type | Affordances | Has Grasping? | Inferred Graspable? |"
    )
    sections.append("| --- | --- | --- | --- | --- |")
    for exp in explanations:
        obj = exp["object"]
        types = ", ".join(exp["types"]) if exp["types"] else "—"
        affs = ", ".join(exp["affordances"]) if exp["affordances"] else "—"
        has_g = "✓" if exp["has_grasping_affordance"] else "✗"
        inferred = "✓ GraspableObject" if exp["inferred_graspable"] else "✗ Not graspable"
        sections.append(f"| {obj} | {types} | {affs} | {has_g} | {inferred} |")
    sections.append("")

    graspable_count = sum(1 for e in explanations if e["inferred_graspable"])
    non_graspable_count = len(explanations) - graspable_count
    sections.append(
        f"**Summary**: {graspable_count} objects inferred as graspable, "
        f"{non_graspable_count} objects not graspable.\n"
    )

    # 4. Class Hierarchy Diagram
    sections.append("## 4. Class Hierarchy Diagram\n")
    sections.append(
        "The following Mermaid diagram shows the `rdfs:subClassOf` "
        "relationships among course and group classes.\n"
    )
    sections.append("```mermaid")
    sections.append(mermaid)
    sections.append("```\n")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    source = load_source_graph()
    inferred = load_inferred_graph()

    metrics = compute_metrics(source, inferred)
    matrix = compute_affordance_matrix(source)
    explanations = compute_graspability_explanations(source, inferred)
    edges = build_class_hierarchy(source)
    mermaid = render_mermaid_hierarchy(edges)

    report = generate_report(metrics, matrix, explanations, mermaid)

    REPORT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUTPUT.write_text(report)

    print(f"Wrote {REPORT_OUTPUT.relative_to(ROOT)}")
    print(f"  Metrics: {metrics['source_triples']} source triples, "
          f"{metrics['inferred_triples']} inferred triples")
    print(f"  Individuals: {metrics['g10_individual_count']} Group 10 instances")
    graspable = sum(1 for e in explanations if e["inferred_graspable"])
    print(f"  Graspability: {graspable}/{len(explanations)} objects inferred graspable")


if __name__ == "__main__":
    main()
