import json
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


class TestSchemas(unittest.TestCase):
    def test_examples_validate_against_schemas(self):
        with open(ROOT / "schemas" / "q-ledger.schema.json", encoding="utf-8") as f:
            q_ledger_schema = json.load(f)
        with open(ROOT / "schemas" / "q-metrics.schema.json", encoding="utf-8") as f:
            q_metrics_schema = json.load(f)

        with open(ROOT / "examples" / "q-ledger.sample.json", encoding="utf-8") as f:
            q_ledger = json.load(f)
        with open(ROOT / "examples" / "q-metrics.sample.json", encoding="utf-8") as f:
            q_metrics = json.load(f)

        jsonschema.validate(q_ledger, q_ledger_schema)
        jsonschema.validate(q_metrics, q_metrics_schema)


if __name__ == "__main__":
    unittest.main()


def test_normalized_request_ndjson_sample_conforms_to_schema() -> None:
    schema_path = ROOT / 'schemas' / 'normalized-request.schema.json'
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    validator = jsonschema.Draft202012Validator(schema)

    ndjson_path = ROOT / 'examples' / 'normalized_requests.sample.ndjson'
    assert ndjson_path.exists()

    with ndjson_path.open('r', encoding='utf-8') as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            errors = sorted(validator.iter_errors(obj), key=lambda e: e.path)
            assert errors == [], f'Line {i} errors: {[e.message for e in errors]}'
