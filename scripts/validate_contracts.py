"""Validate all contract examples against their schemas.

Runs through `docs/contracts/**` and attempts to validate any example
found under `docs/contracts/examples/` against the corresponding schema.

Exit codes:
 - 0: all validations passed
 - 1: one or more validations failed
"""

from pathlib import Path
import json
import sys

from jsonschema import Draft7Validator, RefResolver, exceptions


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "docs" / "contracts"
EXAMPLES = CONTRACTS / "examples"


def _load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def build_store(root: Path):
    store = {}
    for p in root.rglob("*.json"):
        try:
            doc = _load_json(p)
            store[p.resolve().as_uri()] = doc
            store[p.name] = doc
            store[str(p.resolve())] = doc
            # store under $id so Draft-07 $id-scoped $refs resolve without a network fetch
            if "$id" in doc:
                store[doc["$id"]] = doc
        except Exception:
            pass
    return store


def validate_file(schema_path: Path, example_path: Path, store) -> list[str]:
    errors = []
    schema = _load_json(schema_path)
    instance = _load_json(example_path)
    base_uri = schema_path.name
    resolver = RefResolver(base_uri=base_uri, referrer=schema, store=store)
    validator = Draft7Validator(schema, resolver=resolver)
    for e in validator.iter_errors(instance):
        errors.append(f"{example_path}: {e.message} (at {'/'.join(map(str, e.path))})")
    return errors


def main() -> int:
    store = build_store(CONTRACTS)
    examples = list(EXAMPLES.glob("*.json"))
    summary = {"passed": [], "failed": {}}

    for ex in examples:
        # infer schema path by name mapping (simple heuristic)
        name = ex.stem
        mapping = {
            "entityset_example": CONTRACTS / "entity_runtime" / "EntitySet.schema.json",
            "matchset_example": CONTRACTS / "matching_runtime" / "MatchSet.schema.json",
            "review_request_example": CONTRACTS / "review_runtime" / "ReviewRequest.schema.json",
            "review_decision_example": CONTRACTS / "review_runtime" / "ReviewDecision.schema.json",
            "stageresult_example": CONTRACTS / "workflow_runtime" / "StageResult.schema.json",
            "workflowartifact_example": CONTRACTS / "workflow_runtime" / "WorkflowArtifact.schema.json",
        }
        schema_path = mapping.get(name)
        if not schema_path or not schema_path.exists():
            summary["failed"][str(ex)] = ["schema_missing"]
            continue
        errs = validate_file(schema_path, ex, store)
        if errs:
            summary["failed"][str(ex)] = errs
        else:
            summary["passed"].append(str(ex))

    # print summary
    print("Contract validation summary:\n")
    print(f"Passed ({len(summary['passed'])}):")
    for p in summary["passed"]:
        print(f" - {p}")
    print(f"\nFailed ({len(summary['failed'])}):")
    for ex, errs in summary["failed"].items():
        print(f" - {ex}")
        for e in errs:
            print(f"    * {e}")

    return 0 if not summary["failed"] else 1


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
