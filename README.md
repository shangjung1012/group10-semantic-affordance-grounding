# Group 10 Semantic Affordance Grounding

Homework 5 submission for AI Capstone 2026. This project builds a compact ontology layer for grounding baseline task objects and inferring which objects are graspable by a robot gripper.

Repository link: <https://github.com/shangjung1012/group10-semantic-affordance-grounding>

## Group Members

- 蔡尚融
- 江品寬
- 胡占祥
- 楊晟弘
- 林辰翰
- 李冠緯

## Selected Task

Our group's final project task is toy block collection.

For Homework 5, this submission also includes the required baseline object vocabulary and instances from all three predefined course tasks:

- Cup stacking: blue cup and pink cup
- Cutlery arrangement: knife, fork, and plate
- Toy block collection: toy blocks and basket

## Repository Structure

```text
.
|-- README.md
|-- report.md
|-- ontology/
|   |-- group-ontology.ttl
|   |-- shapes.ttl
|   |-- inferred-results.ttl
|   `-- imports/
|       |-- course-affordance.ttl
|       `-- course-alignment.ttl
|-- queries/
|   |-- graspable_objects.rq
|   `-- task_objects.rq
|-- results/
|   |-- graspable_objects_output.txt
|   |-- task_objects_output.txt
|   `-- shacl_validation_output.txt
|-- src/
|   |-- run_reasoning.py
|   `-- run_validation.py
|-- tests/
|   |-- test_hw5_workflow.py
|   `-- test_shacl_validation.py
|-- pyproject.toml
`-- uv.lock
```

`ontology/group-ontology.ttl` and `ontology/shapes.ttl` are Group 10 authored files. Files under `ontology/imports/` are copied course starter resources and are treated as imported dependencies, not as Group 10 authored ontology files.

## Key File Links

- Group ontology: [`ontology/group-ontology.ttl`](ontology/group-ontology.ttl)
- Inferred graph: [`ontology/inferred-results.ttl`](ontology/inferred-results.ttl)
- Course imports: [`ontology/imports/course-affordance.ttl`](ontology/imports/course-affordance.ttl), [`ontology/imports/course-alignment.ttl`](ontology/imports/course-alignment.ttl)
- Required query: [`queries/graspable_objects.rq`](queries/graspable_objects.rq)
- Additional query: [`queries/task_objects.rq`](queries/task_objects.rq)
- Reasoning workflow: [`src/run_reasoning.py`](src/run_reasoning.py)
- SHACL shapes: [`ontology/shapes.ttl`](ontology/shapes.ttl)
- SHACL validation workflow: [`src/run_validation.py`](src/run_validation.py)
- Query outputs: [`results/graspable_objects_output.txt`](results/graspable_objects_output.txt), [`results/task_objects_output.txt`](results/task_objects_output.txt)
- SHACL validation output: [`results/shacl_validation_output.txt`](results/shacl_validation_output.txt)
- Report: [`report.md`](report.md)
- Widoco documentation: [`docs/widoco/group-ontology/doc/index-en.html`](docs/widoco/group-ontology/doc/index-en.html)

## Namespace Policy

- Course vocabulary: `cap: <https://hcis.io/ontology/aicapstone/2026/>`
- Group 10 vocabulary and instances: `g10: <https://hcis.io/ontology/aicapstone/2026/group10/>`

Shared classes and properties such as `cap:Cup`, `cap:hasAffordance`, and `cap:GraspableObject` use the `cap:` namespace. Group-specific individuals such as `g10:blueCup01` and `g10:targetObjectRole` use the `g10:` namespace.

## Ontology Design

The ontology separates object type, task role, affordance, and instance. Graspability is inferred from the pattern:

```text
cap:PhysicalObject and hasAffordance some cap:GraspingAffordance
```

The group ontology defines the formal `cap:GraspableObject` class axiom because the provided starter ontology documents the course-level term but does not include the full OWL class definition. This is a formalization of an existing course term, not a new Group 10 class in the `cap:` namespace.

Task roles are represented with Group 10 role individuals, such as `g10:targetObjectRole a cap:TargetObject`, instead of using course role classes directly as `cap:hasTaskRole` values.

| Object | Type | Role | Affordance | Graspable result |
| --- | --- | --- | --- | --- |
| `g10:blueCup01` | `cap:Cup` | `cap:TargetObject` | grasping, stackability | inferred |
| `g10:pinkCup01` | `cap:Cup` | `cap:TargetObject` | grasping, stackability | inferred |
| `g10:knife01` | `cap:Knife` | `cap:TargetObject` | grasping | inferred |
| `g10:fork01` | `cap:Fork` | `cap:TargetObject` | grasping | inferred |
| `g10:plate01` | `cap:Plate` | `cap:ReferenceObject` | support | not inferred |
| `g10:block01` | `cap:ToyBlock` | `cap:CollectableObject` | grasping | inferred |
| `g10:block02` | `cap:ToyBlock` | `cap:CollectableObject` | grasping | inferred |
| `g10:basket01` | `cap:Basket` | `cap:ContainerTarget` | containment | not inferred |

Plate and basket are task-relevant but are not modeled as direct grasp targets in this baseline submission.

## Running Locally

This project uses `uv`.

```bash
uv sync
uv run python src/run_reasoning.py
```

The script writes:

- `ontology/inferred-results.ttl`
- `results/graspable_objects_output.txt`
- `results/task_objects_output.txt`

Run the SHACL structural validation with:

```bash
uv run python src/run_validation.py
```

This writes `results/shacl_validation_output.txt`.

Run verification tests with:

```bash
uv run pytest
```

## SHACL Validation

OWL/RDFS reasoning and SHACL validation play complementary roles in this submission. The reasoning workflow (`src/run_reasoning.py`) *infers* class membership such as `cap:GraspableObject`. SHACL, in contrast, *checks* that the submitted graph satisfies the required structural constraints, as recommended in the homework specification (Section 15).

The Group 10 shapes in [`ontology/shapes.ttl`](ontology/shapes.ttl) enforce:

- every `cap:PhysicalObject` records at least one `cap:hasObjectLabel`;
- every `cap:PhysicalObject` has at least one `cap:hasTaskRole` whose value is a `cap:TaskRole`;
- every `cap:PhysicalObject` has at least one `cap:hasAffordance` whose value is a `cap:Affordance`;
- every object declared `cap:canBeManipulatedBy` an end effector also has at least one `cap:GraspingAffordance`.

Because instances are typed with course subclasses (e.g. `cap:Cup`), validation is run with RDFS inference and the course ontology supplied as the ontology graph, so that `sh:targetClass cap:PhysicalObject` matches every instance. The baseline graph conforms to all four shapes.

## Widoco Documentation Check

Widoco 1.4.25 was run on `ontology/group-ontology.ttl` as an ontology documentation check. The documentation was generated successfully under `docs/widoco/group-ontology/doc/index-en.html`, and it lists the ontology metadata, imported course ontology, `cap:GraspableObject` equivalent-class axiom, and modeled task-object individuals.

## Expected Graspable Query Output

`queries/graspable_objects.rq` runs over the inferred graph and should return:

```text
g10:block01
g10:block02
g10:blueCup01
g10:fork01
g10:knife01
g10:pinkCup01
```

The query output is saved in `results/graspable_objects_output.txt`.

## What Is Inferred

The group ontology does not manually assert Group 10 objects as `cap:GraspableObject`. Instead, `src/run_reasoning.py` loads the course affordance ontology, course alignment ontology, and group ontology, applies OWL/RDFS closure with `owlrl`, then materializes the assignment-specific rule: a physical object with a grasping affordance is typed as `cap:GraspableObject`.

This produces inferred graspable memberships for cups, knife, fork, and toy blocks. Plate and basket remain outside the graspable result because their asserted affordances are support and containment, respectively.
