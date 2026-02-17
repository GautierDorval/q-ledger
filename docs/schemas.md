# Schemas

This repo ships JSON Schemas for the public artifacts:

- `schemas/q-ledger.schema.json`
- `schemas/q-metrics.schema.json`

These schemas make the formats machine-verifiable and reduce evaluator variance when ingesting snapshots.

## Validate examples locally

If you have `jsonschema` installed:

```bash
python -c "import json; import jsonschema; s=json.load(open('schemas/q-ledger.schema.json')); d=json.load(open('examples/q-ledger.sample.json')); jsonschema.validate(d,s); print('q-ledger OK')"
```

```bash
python -c "import json; import jsonschema; s=json.load(open('schemas/q-metrics.schema.json')); d=json.load(open('examples/q-metrics.sample.json')); jsonschema.validate(d,s); print('q-metrics OK')"
```
