"""Tests for the ontology analysis and visualization module."""

from pathlib import Path
import subprocess
import sys

from rdflib import Graph, Namespace, RDF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_analysis import (
    compute_affordance_matrix,
    compute_graspability_explanations,
    compute_metrics,
    build_class_hierarchy,
    load_inferred_graph,
    load_source_graph,
    render_mermaid_hierarchy,
)

CAP = Namespace("https://hcis.io/ontology/aicapstone/2026/")
G10 = Namespace("https://hcis.io/ontology/aicapstone/2026/group10/")

REPORT_OUTPUT = ROOT / "results/analysis_report.md"

EXPECTED_G10_OBJECTS = {
    "g10:blueCup01",
    "g10:pinkCup01",
    "g10:knife01",
    "g10:fork01",
    "g10:plate01",
    "g10:block01",
    "g10:block02",
    "g10:basket01",
}

EXPECTED_GRASPABLE = {
    "g10:blueCup01",
    "g10:pinkCup01",
    "g10:knife01",
    "g10:fork01",
    "g10:block01",
    "g10:block02",
}

EXPECTED_NOT_GRASPABLE = {
    "g10:plate01",
    "g10:basket01",
}


def test_source_graph_loads() -> None:
    source = load_source_graph()
    assert len(source) > 0


def test_inferred_graph_loads() -> None:
    inferred = load_inferred_graph()
    assert len(inferred) > 0


def test_metrics_have_expected_keys() -> None:
    source = load_source_graph()
    inferred = load_inferred_graph()
    metrics = compute_metrics(source, inferred)

    required_keys = {
        "source_triples",
        "inferred_triples",
        "class_count",
        "cap_class_count",
        "g10_class_count",
        "object_property_count",
        "datatype_property_count",
        "g10_individual_count",
    }
    assert required_keys <= set(metrics.keys())


def test_metrics_values_are_reasonable() -> None:
    source = load_source_graph()
    inferred = load_inferred_graph()
    metrics = compute_metrics(source, inferred)

    assert metrics["source_triples"] > 0
    assert metrics["inferred_triples"] >= metrics["source_triples"]
    assert metrics["class_count"] >= 4
    assert metrics["g10_individual_count"] >= 8
    assert metrics["object_property_count"] >= 1
    assert metrics["datatype_property_count"] >= 1


def test_affordance_matrix_covers_all_objects() -> None:
    source = load_source_graph()
    matrix = compute_affordance_matrix(source)

    object_names = {row["object"] for row in matrix}
    assert EXPECTED_G10_OBJECTS <= object_names


def test_affordance_matrix_has_correct_affordance_columns() -> None:
    source = load_source_graph()
    matrix = compute_affordance_matrix(source)

    for row in matrix:
        for key in ("Grasping", "Support", "Containment", "Stackability"):
            assert key in row


def test_graspability_explanations_identify_graspable_objects() -> None:
    source = load_source_graph()
    inferred = load_inferred_graph()
    explanations = compute_graspability_explanations(source, inferred)

    graspable = {e["object"] for e in explanations if e["inferred_graspable"]}
    not_graspable = {e["object"] for e in explanations if not e["inferred_graspable"]}

    assert EXPECTED_GRASPABLE <= graspable
    assert EXPECTED_NOT_GRASPABLE <= not_graspable


def test_graspability_count() -> None:
    source = load_source_graph()
    inferred = load_inferred_graph()
    explanations = compute_graspability_explanations(source, inferred)

    graspable_count = sum(1 for e in explanations if e["inferred_graspable"])
    non_graspable_count = sum(1 for e in explanations if not e["inferred_graspable"])

    assert graspable_count == 6
    assert non_graspable_count == 2


def test_class_hierarchy_has_edges() -> None:
    source = load_source_graph()
    edges = build_class_hierarchy(source)

    assert len(edges) > 0

    # At minimum, cap:Cup rdfs:subClassOf cap:PhysicalObject should be present
    child_names = {child for child, _ in edges}
    assert "cap:Cup" in child_names


def test_mermaid_rendering_produces_valid_output() -> None:
    source = load_source_graph()
    edges = build_class_hierarchy(source)
    mermaid = render_mermaid_hierarchy(edges)

    assert mermaid.startswith("graph TD")
    assert "-->" in mermaid


def test_analysis_script_generates_report() -> None:
    subprocess.run(
        [sys.executable, "src/run_analysis.py"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert REPORT_OUTPUT.exists()
    content = REPORT_OUTPUT.read_text()

    assert "# Ontology Analysis Report" in content
    assert "## 1. Ontology Metrics" in content
    assert "## 2. Affordance Coverage Matrix" in content
    assert "## 3. Graspability Reasoning Explanation" in content
    assert "## 4. Class Hierarchy Diagram" in content
    assert "```mermaid" in content
