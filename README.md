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
Copy and edit the example config:

- `config/example.env` → `.env` (do **not** commit)
- `config/example.com.yml` → `config/<your-domain>.yml`

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

---

## Status

Experimental. The format is stable enough for real deployments, but expect iterative improvements to scripts and documentation.
