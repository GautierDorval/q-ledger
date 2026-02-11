# Runbook — q-ledger (manual mode)

## Cadence
- Daily (recommended) OR every 48 hours.
- Always use the same time window strategy to reduce drift.

## Step 1 — Export Cloudflare logs
- Cloudflare Log Search
- Time window: last 24h (daily) OR last 48h (48h cadence)
- Query: governance filters used for q-ledger
- Export: CSV

## Step 2 — Archive raw export
- Save as: exports/cloudflare-http-requests-YYYY-MM-DD.csv

## Step 3 — Replace pipeline input
- Copy export to: input/cloudflare_logs.csv

## Step 4 — Build ledger
- Run: python scripts/build_ledger.py
- Output: out/q-ledger.json, out/q-ledger.yml, out/q-ledger-latest.json
- State: state/ledger-state.json (sequence + previous hash)

## Step 5 — Generate metrics markdown
- Run: python scripts/metrics.py out/q-ledger.json out/metrics.md

## Step 6 — Archive ledger + metrics
- Copy:
  - out/q-ledger.json -> ledgers/q-ledger-YYYY-MM-DD-seqNN.json
  - out/q-ledger.yml  -> ledgers/q-ledger-YYYY-MM-DD-seqNN.yml
  - out/metrics.md    -> ledgers/metrics-YYYY-MM-DD-seqNN.md

## Step 7 — Publish (clipboard assist)
- Run: .\scripts\publish.ps1
- Paste into:
  - /.well-known/q-ledger.json
  - /.well-known/q-ledger.yml

## Step 8 — Verify public endpoints
- https://example.com/.well-known/q-ledger.json
- https://example.com/.well-known/q-ledger.yml
