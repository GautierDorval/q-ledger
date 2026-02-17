# Input normalization

Q-Ledger is designed to be provider-agnostic, but real-world edge logs come in many formats (Cloudflare, Nginx, ALB, …).

To reduce lock-in and increase reusability, this repo defines a minimal intermediate format:

- **NormalizedRequest** (one request per line)
- output as **NDJSON** (recommended) or **CSV**

## NormalizedRequest format

Each record contains only the fields needed for session inference and governance metrics:

Required:
- `ts` (ISO 8601, date-time)
- `method`
- `path` (path only, no scheme/host)
- `status` (100–599)

Optional:
- `host`
- `ip`
- `user_agent`
- `provider`
- `request_id`

Schema:
- `schemas/normalized-request.schema.json`

Example:
- `examples/normalized_requests.sample.ndjson`

## Adapters

The normalization script supports multiple inputs:

- `cloudflare_csv` (Cloudflare Log Search CSV export)
- `nginx_combined` (Nginx combined access log)
- `aws_alb` (AWS ALB access logs, best-effort)
- `generic_jsonl` (JSON lines with key mapping)

### Usage

Cloudflare CSV to NDJSON:

```bash
python scripts/normalize_input.py   --provider cloudflare_csv   --input input/cloudflare_logs.csv   --output input/normalized_requests.ndjson
```

Nginx combined (requires `--default-host` unless your log format includes host):

```bash
python scripts/normalize_input.py   --provider nginx_combined   --input input/nginx-access.log   --default-host example.com   --output input/normalized_requests.ndjson
```

AWS ALB:

```bash
python scripts/normalize_input.py   --provider aws_alb   --input input/alb-access.log   --output input/normalized_requests.ndjson
```

Generic JSONL:

```bash
python scripts/normalize_input.py   --provider generic_jsonl   --input input/provider.jsonl   --output input/normalized_requests.ndjson   --key-ts time   --key-method method   --key-path path   --key-status status
```

## Feeding NDJSON into Q-Ledger

`build_ledger.py` supports NDJSON when:
- `config.input.format` is set to `normalized_ndjson`, **or**
- the input file ends with `.ndjson` / `.jsonl`

You must also adjust `config.input.columns` to match NDJSON keys (lowercase recommended), for example:

```json
{
  "input": {
    "format": "normalized_ndjson",
    "csv_path": "input/normalized_requests.ndjson",
    "columns": {
      "timestamp": "ts",
      "ip": "ip",
      "ua": "user_agent",
      "host": "host",
      "path": "path",
      "method": "method",
      "status": "status"
    }
  }
}
```
