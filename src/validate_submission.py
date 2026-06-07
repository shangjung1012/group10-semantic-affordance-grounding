from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from rdflib import Graph, Namespace, RDF, URIRef

from run_reasoning import ROOT, format_rows, load_graph, run_reasoning


CAP = Namespace("https://hcis.io/ontology/aicapstone/2026/")
G10 = Namespace("https://hcis.io/ontology/aicapstone/2026/group10/")

REQUIRED_FILES = [
    ROOT / "README.md",
    ROOT / "report.md",
    ROOT / "ontology/group-ontology.ttl",
    ROOT / "ontology/imports/course-affordance.ttl",
    ROOT / "ontology/imports/course-alignment.ttl",
    ROOT / "ontology/inferred-results.ttl",
    ROOT / "queries/graspable_objects.rq",
    ROOT / "queries/task_objects.rq",
    ROOT / "queries/non_graspable_task_objects.rq",
    ROOT / "queries/object_affordance_summary.rq",
    ROOT / "results/graspable_objects_output.txt",
    ROOT / "results/task_objects_output.txt",
    ROOT / "results/non_graspable_task_objects_output.txt",
    ROOT / "results/object_affordance_summary_output.txt",
    ROOT / "src/run_reasoning.py",
    ROOT / "src/validate_submission.py",
    ROOT / "tests/test_hw5_workflow.py",
]

EXPECTED_TASK_OBJECTS = {
    G10.blueCup01: {
        "type": CAP.Cup,
        "label": "blue_cup",
        "color": "blue",
        "role": CAP.TargetObject,
        "graspable": True,
    },
    G10.pinkCup01: {
        "type": CAP.Cup,
        "label": "pink_cup",
        "color": "pink",
        "role": CAP.TargetObject,
        "graspable": True,
    },
    G10.knife01: {
        "type": CAP.Knife,
        "label": "knife",
        "color": "silver",
        "role": CAP.TargetObject,
        "graspable": True,
    },
    G10.fork01: {
        "type": CAP.Fork,
        "label": "fork",
        "color": "silver",
        "role": CAP.TargetObject,
        "graspable": True,
    },
    G10.plate01: {
        "type": CAP.Plate,
        "label": "plate",
        "color": "white",
        "role": CAP.ReferenceObject,
        "graspable": False,
    },
    G10.block01: {
        "type": CAP.ToyBlock,
        "label": "toy_block_red",
        "color": "red",
        "role": CAP.CollectableObject,
        "graspable": True,
    },
    G10.block02: {
        "type": CAP.ToyBlock,
        "label": "toy_block_yellow",
        "color": "yellow",
        "role": CAP.CollectableObject,
        "graspable": True,
    },
    G10.basket01: {
        "type": CAP.Basket,
        "label": "basket",
        "color": "green",
        "role": CAP.ContainerTarget,
        "graspable": False,
    },
}


def compact(value: URIRef) -> str:
    if str(value).startswith(str(G10)):
        return f"g10:{str(value).removeprefix(str(G10))}"
    if str(value).startswith(str(CAP)):
        return f"cap:{str(value).removeprefix(str(CAP))}"
    return str(value)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_required_files() -> None:
    missing = [path.relative_to(ROOT).as_posix() for path in REQUIRED_FILES if not path.exists()]
    require(not missing, f"Missing required files: {', '.join(missing)}")


def check_turtle_files_parse() -> None:
    for path in [
        ROOT / "ontology/group-ontology.ttl",
        ROOT / "ontology/imports/course-affordance.ttl",
        ROOT / "ontology/imports/course-alignment.ttl",
        ROOT / "ontology/inferred-results.ttl",
    ]:
        Graph().parse(path, format="turtle")


def check_group_ontology_modeling(graph: Graph) -> None:
    for obj, expected in EXPECTED_TASK_OBJECTS.items():
        require((obj, RDF.type, expected["type"]) in graph, f"{compact(obj)} has wrong type")
        require(
            (obj, CAP.hasObjectLabel, None) in graph,
            f"{compact(obj)} is missing cap:hasObjectLabel",
        )
        require(
            expected["label"] in {str(label) for label in graph.objects(obj, CAP.hasObjectLabel)},
            f"{compact(obj)} has wrong object label",
        )
        require(
            expected["color"] in {str(color) for color in graph.objects(obj, CAP.hasColor)},
            f"{compact(obj)} has wrong color",
        )
        require(
            (obj, CAP.hasPoseFrame, None) in graph,
            f"{compact(obj)} is missing cap:hasPoseFrame",
        )
        require(
            (obj, CAP.hasAffordance, None) in graph,
            f"{compact(obj)} is missing cap:hasAffordance",
        )

        role_values = set(graph.objects(obj, CAP.hasTaskRole))
        require(role_values, f"{compact(obj)} is missing cap:hasTaskRole")
        require(
            any((role, RDF.type, expected["role"]) in graph for role in role_values),
            f"{compact(obj)} has wrong task role",
        )

    manually_asserted = {
        compact(subject)
        for subject in graph.subjects(RDF.type, CAP.GraspableObject)
        if str(subject).startswith(str(G10))
    }
    require(
        not manually_asserted,
        "Group objects should be inferred as graspable, not manually asserted: "
        + ", ".join(sorted(manually_asserted)),
    )


def check_reasoned_graspable_results(graph: Graph) -> None:
    inferred = run_reasoning(graph)
    inferred_graspable = {
        subject
        for subject in inferred.subjects(RDF.type, CAP.GraspableObject)
        if str(subject).startswith(str(G10))
    }

    expected_graspable = {
        obj for obj, expected in EXPECTED_TASK_OBJECTS.items() if expected["graspable"]
    }
    expected_excluded = set(EXPECTED_TASK_OBJECTS) - expected_graspable

    require(
        inferred_graspable == expected_graspable,
        "Unexpected graspable set. Expected "
        + ", ".join(sorted(compact(obj) for obj in expected_graspable))
        + "; got "
        + ", ".join(sorted(compact(obj) for obj in inferred_graspable)),
    )
    require(
        expected_excluded.isdisjoint(inferred_graspable),
        "Non-graspable objects appeared in graspable results",
    )


def check_saved_query_outputs_match_reasoning(graph: Graph) -> None:
    inferred = run_reasoning(graph)
    for query_path, output_path in {
        ROOT / "queries/graspable_objects.rq": ROOT / "results/graspable_objects_output.txt",
        ROOT / "queries/task_objects.rq": ROOT / "results/task_objects_output.txt",
        ROOT / "queries/non_graspable_task_objects.rq": (
            ROOT / "results/non_graspable_task_objects_output.txt"
        ),
        ROOT / "queries/object_affordance_summary.rq": (
            ROOT / "results/object_affordance_summary_output.txt"
        ),
    }.items():
        query_result = inferred.query(query_path.read_text())
        expected_output = format_rows(inferred, query_result, [str(var) for var in query_result.vars])
        actual_output = output_path.read_text()
        require(
            actual_output == expected_output,
            f"{output_path.relative_to(ROOT)} is stale; run src/run_reasoning.py",
        )


def check_inferred_output_is_portable() -> None:
    output = (ROOT / "ontology/inferred-results.ttl").read_text()
    require(ROOT.as_posix() not in output, "Inferred output contains this machine's repo path")
    require("file://" not in output, "Inferred output contains file:// import IRIs")
    require(
        "<imports/course-affordance.ttl>" in output,
        "Inferred output should retain the relative course ontology import",
    )


def run_check(name: str, check: Callable[[], None]) -> None:
    check()
    print(f"ok - {name}")


def main() -> None:
    source_graph = load_graph()
    checks: list[tuple[str, Callable[[], None]]] = [
        ("required files are present", check_required_files),
        ("Turtle files parse", check_turtle_files_parse),
        ("group ontology models required task objects", lambda: check_group_ontology_modeling(source_graph)),
        ("graspable objects are inferred as expected", lambda: check_reasoned_graspable_results(source_graph)),
        ("saved query outputs match current reasoning", lambda: check_saved_query_outputs_match_reasoning(source_graph)),
        ("inferred ontology output is portable", check_inferred_output_is_portable),
    ]
    for name, check in checks:
        run_check(name, check)


if __name__ == "__main__":
    main()
