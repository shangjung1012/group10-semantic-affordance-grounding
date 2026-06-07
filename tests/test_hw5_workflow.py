from pathlib import Path
import subprocess
import sys

from rdflib import Graph, Namespace, RDF


ROOT = Path(__file__).resolve().parents[1]
CAP = Namespace("https://hcis.io/ontology/aicapstone/2026/")
G10 = Namespace("https://hcis.io/ontology/aicapstone/2026/group10/")


def parse_turtle(path: Path) -> Graph:
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def test_course_and_group_ontologies_parse_as_turtle() -> None:
    parse_turtle(ROOT / "ontology/imports/course-affordance.ttl")
    parse_turtle(ROOT / "ontology/group-ontology.ttl")


def test_group_ontology_does_not_assert_graspable_membership() -> None:
    graph = parse_turtle(ROOT / "ontology/group-ontology.ttl")
    asserted_graspable = {
        subject
        for subject in graph.subjects(RDF.type, CAP.GraspableObject)
        if str(subject).startswith(str(G10))
    }
    assert asserted_graspable == set()


def test_task_role_values_are_group_role_individuals() -> None:
    graph = parse_turtle(ROOT / "ontology/group-ontology.ttl")
    role_values = set(graph.objects(None, CAP.hasTaskRole))

    assert role_values
    assert all(str(role).startswith(str(G10)) for role in role_values)


def test_reasoning_script_generates_expected_graspable_objects() -> None:
    subprocess.run(
        [sys.executable, "src/run_reasoning.py"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    inferred = parse_turtle(ROOT / "ontology/inferred-results.ttl")
    inferred_graspable = {
        subject
        for subject in inferred.subjects(RDF.type, CAP.GraspableObject)
        if str(subject).startswith(str(G10))
    }

    expected = {
        G10.blueCup01,
        G10.pinkCup01,
        G10.knife01,
        G10.fork01,
        G10.block01,
        G10.block02,
    }
    excluded = {G10.plate01, G10.basket01}

    assert expected <= inferred_graspable
    assert excluded.isdisjoint(inferred_graspable)


def test_saved_graspable_output_matches_expected_objects() -> None:
    subprocess.run(
        [sys.executable, "src/run_reasoning.py"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    output = (ROOT / "results/graspable_objects_output.txt").read_text()

    for name in ["blueCup01", "pinkCup01", "knife01", "fork01", "block01", "block02"]:
        assert name in output

    assert "plate01" not in output
    assert "basket01" not in output


def test_reasoning_output_is_stable_across_runs() -> None:
    first_output = None

    for run_index in range(2):
        subprocess.run(
            [sys.executable, "src/run_reasoning.py"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        current_output = (ROOT / "ontology/inferred-results.ttl").read_text()

        if run_index == 0:
            first_output = current_output

    assert current_output == first_output


def test_inferred_results_do_not_contain_local_absolute_paths() -> None:
    subprocess.run(
        [sys.executable, "src/run_reasoning.py"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    output = (ROOT / "ontology/inferred-results.ttl").read_text()

    assert ROOT.as_posix() not in output
    assert "file://" not in output
    assert "<imports/course-affordance.ttl>" in output
