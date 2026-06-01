"""Helpers for contract validation tests.

Provides a small `validate_example` helper that loads JSON Schema Draft 07
files and validates example fixtures using `jsonschema` with a resolver that
pre-loads all schemas under `docs/contracts/` to support relative `$ref`s.
"""

from pathlib import Path
import json

from jsonschema import Draft7Validator, RefResolver


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _build_store(root: Path):
    store = {}
    for p in root.rglob("*.json"):
        try:
            doc = _load_json(p)
            # store under full file URI
            store[p.resolve().as_uri()] = doc
            # store under filename to help relative $ref lookups (e.g., "StageResult.schema.json")
            store[p.name] = doc
            # store under absolute filesystem path string
            store[str(p.resolve())] = doc
            # store under $id so Draft-07 $id-scoped $refs resolve without a network fetch
            if "$id" in doc:
                store[doc["$id"]] = doc
        except Exception:
            # best-effort: ignore unreadable files
            pass
    return store


def validate_example(schema_file: str | Path, example_file: str | Path) -> None:
    schema_path = Path(schema_file).resolve()
    example_path = Path(example_file).resolve()
    schema = _load_json(schema_path)
    instance = _load_json(example_path)

    root = Path("docs/contracts").resolve()
    store = _build_store(root)

    # When a schema declares $id as a URN (e.g. "urn:project:..."), Python's
    # urljoin cannot resolve relative $refs from that base because "urn" is not
    # in urllib's uses_relative set.  Two consequences:
    #
    #  1. First-level $refs:  urljoin("urn:...", "#/definitions/X") returns
    #     "#/definitions/X"; urldefrag gives url=""; RefResolver then falls back
    #     to base_uri which equals urldefrag(resolution_scope)[0] = "urn:...".
    #     Fix: store[$id] entry (added in _build_store) makes the lookup succeed.
    #
    #  2. Nested $refs:  after push_scope("#/definitions/X"), resolution_scope
    #     becomes "#/definitions/X" (fragment-only), so base_uri degrades to "".
    #     Fix: store[""] points to the current schema so the lookup still works.
    store[""] = schema

    base_uri = schema_path.name
    resolver = RefResolver(base_uri=base_uri, referrer=schema, store=store)
    validator = Draft7Validator(schema, resolver=resolver)
    validator.validate(instance)
