from pathlib import Path
import json
def _load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def _build_store(root: Path):
    store = {}
    for p in root.rglob('*.json'):
        try:
            doc = _load_json(p)
            store[p.resolve().as_uri()] = doc
            store[p.name] = doc
            store[str(p.resolve())] = doc
        except Exception:
            pass
    return store


def inspect(schema_rel_path):
    schema_path = Path(schema_rel_path).resolve()
    schema = _load_json(schema_path)
    root = Path('docs/contracts').resolve()
    store = _build_store(root)
    base_uri = schema_path.name
    print('Schema path:', schema_path)
    print('Base URI used:', base_uri)
    print('Store has base_uri key:', base_uri in store)
    print('Store sample keys:')
    keys = list(store.keys())[:20]
    for k in keys:
        print(' -', k)
    # attempt validation to reproduce error
    ex_path = schema_path.parent.parent / 'examples' / (schema_path.stem.lower() + '_example.json')
    if ex_path.exists():
        print('\nValidating example:', ex_path)
        from jsonschema import Draft7Validator, RefResolver

        resolver = RefResolver(base_uri=schema_path.name, referrer=schema, store=store)
        validator = Draft7Validator(schema, resolver=resolver)
        try:
            instance = _load_json(ex_path)
            validator.validate(instance)
            print('Validation: OK')
        except Exception as e:
            print('Validation error:', type(e), e)


if __name__ == '__main__':
    print('--- EntitySet ---')
    inspect('docs/contracts/entity_runtime/EntitySet.schema.json')
    print('\n--- MatchSet ---')
    inspect('docs/contracts/matching_runtime/MatchSet.schema.json')
