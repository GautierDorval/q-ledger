# Q-Ledger

Q-Ledger is a machine-first, log-derived ledger format used to publish **verifiable governance snapshots** (entrypoints + derived metrics) from edge request observation.  
It is designed to reduce interpretive drift by making governance artifacts **discoverable, traceable, and chain-linked** over time—without exposing raw logs.

> Scope: **observation, not attestation**.  
> Q-Ledger does not prove identity, authorship, or intent. It only publishes structured evidence derived from server/edge request visibility.

---

## What Q-Ledger is

- An **append-only** publication format (JSON + YAML) for governance entrypoints.
- A **chain-linked** sequence using `previous_ledger_hash_sha256` to make silent edits detectable.
- A way to publish:
  - what was observed as requested at the edge (derived from logs), and
  - a minimal set of integrity and stability signals (“Q-Metrics”).

## What Q-Ledger is not

- Not a security attestation system.
- Not a cryptographic identity proof.
- Not a replacement for signed releases, certificates, or transparency logs.
- Not a recommendation engine or a compliance claim.

---

## Files and endpoints

A typical deployment publishes machine-readable endpoints such as:

- `/.well-known/q-ledger.json`
- `/.well-known/q-ledger.yml`
- `/.well-known/q-metrics.json`
- `/.well-known/q-metrics.yml`

These are intended to be public, cacheable, and easy to crawl.

## Post-publication verification

Manual publishing is fast, but error-prone.

Use the verifier to re-fetch your public endpoints and compare canonical hashes vs local outputs:

- PowerShell: `scripts/verify-publication.ps1`
- Python: `scripts/verify_publication.py`

See: `docs/post-publication-verification.md`

## Multi-provider input normalization

If your logs are not Cloudflare CSV, normalize them first into a provider-agnostic intermediate format (NDJSON recommended):

- Script: `scripts/normalize_input.py`
- Schema: `schemas/normalized-request.schema.json`

See: `docs/input-normalization.md`

## Ecosystem positioning

Q-Ledger is observational by design.

See: `docs/ecosystem.md`


---

## Data model (high level)

Q-Ledger entries usually include:

- **Observed requests** (aggregated): method, path, status, timestamps, host.
- **Entrypoint coverage**: whether expected governance entrypoints were observed.
- **Chain linkage**: current hash + previous hash for continuity.
- **Derived signals (Q-Metrics)**: basic stability/compliance indicators computed from the ledger.

This repository contains:
- scripts to build and update the ledger,
- documentation for the format and operational workflow,
- redacted examples (no raw logs, no IPs, no secrets).

---

## Quick start

### 1) Requirements
- Python 3.10+ (recommended)
- Access to edge logs (e.g., Cloudflare logs export) **stored locally**
- A private salt/secret used only for hashing/normalization

### 2) Configure

This repo is meant to be reusable. To avoid committing deployment-specific settings, use the **`.local`** config convention.

#### Environment

Set a fingerprint salt (required):

- `Q_LEDGER_SALT` (recommended) or
- any env var name referenced by `fingerprint_salt_env` in your config

A template exists: `config/example.env` (do not commit real salts).

#### Config files

Copy templates to local, uncommitted configs:

- `config/config.example.json` → `config/config.local.json`
- `config/governance_scope.example.json` → `config/governance_scope.local.json` (optional, but recommended)

Then edit `config/config.local.json`:

- `site` (base URL, e.g. `https://example.com/`)
- `input.csv_path` (default: `input/cloudflare_logs.csv`)
- `output.*` paths

The scripts resolve config paths in this order:

1. `--config` / `--scope` (CLI, where supported)
2. `Q_LEDGER_CONFIG_PATH` / `Q_LEDGER_SCOPE_PATH`
3. `config/*.local.json`
4. committed demo defaults: `config/config.json`, `config/governance_scope.json`
5. templates: `config/config.example.json`, `config/governance_scope.example.json`

#### Disclosure token

`q-metrics.json` includes `disclosure_token` as an intent marker (not a secret, not authentication).

- Default: `Q-LEDGER-DISCLOSED`
- Override: set `Q_LEDGER_DISCLOSURE_TOKEN` or set `q_metrics.disclosure_token` in config.

See `docs/disclosure-token.md`.


### 3) Build ledger
Run the main builder script (see `scripts/`):

- Build/update `q-ledger`
- Compute `q-metrics`
- Output JSON + YAML files ready to publish under `/.well-known/`

> See `RUNBOOK.md` for the recommended operational workflow and publishing steps.

---

## Privacy and safety

This project is intentionally designed to avoid publishing:
- raw logs,
- IP addresses,
- full user agents,
- internal IDs or tokens.

Only **aggregated / derived** evidence should be emitted publicly.

---

## Roadmap

- `q-attest` (optional future layer): signed attestations over published ledger snapshots
- schema validation (JSON Schema) + conformance labels
- automated archive publisher (GitHub Actions) for daily snapshotting

---

## License

Choose a license that matches your intent (MIT/Apache-2.0 for wide adoption, or a more restrictive license if needed).  
See `LICENSE` for the current selection.
Licensed under the Apache License 2.0. See `LICENSE` and `NOTICE`.

---

## Status

Experimental. The format is stable enough for real deployments, but expect iterative improvements to scripts and documentation.


## Related work (ecosystem)

Q-Ledger is an operational observability artifact. If you are looking for the broader governance doctrine and evaluation tooling, see:

- `interpretive-governance-manifest` (governance surfaces & discovery protocol)
- `interpretive-governance-test-suite` (conformance tests)
- `iip-scoring-standard` (depth-oriented integrity scoring)

These repos are complementary: Q-Ledger / Q-Metrics are observational signals derived from edge logs, while scoring and test suites focus on normative validation and audit depth.
