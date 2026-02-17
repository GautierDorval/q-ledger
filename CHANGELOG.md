# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to semantic versioning.

## [0.1.1] - 2026-02-17

### Added
- JSON Schemas for `q-ledger` and `q-metrics` under `schemas/`.
- Unit tests for critical hashing/parsing/session-inference functions.
- GitHub Actions CI workflow (Python 3.11, 3.12).
- `input_stats` in Q-Ledger output (rows total/loaded/skipped).
- Post-publication verification scripts (`scripts/verify-publication.ps1`, `scripts/verify_publication.py`).
- Provider-agnostic input normalization (`scripts/normalize_input.py`) and `NormalizedRequest` schema.
- NDJSON input support in `build_ledger.py` (via `config.input.format` or file extension).
- Ecosystem positioning docs (`docs/ecosystem.md`).

### Changed
- `q_metrics.disclosure_token` is now configurable (default: `Q-LEDGER-DISCLOSED`).
- Removed hardcoded site traceability URLs from Q-Metrics generation. URLs are now derived from `site` + configurable paths.
- Config resolution now supports `config/*.local.json` (gitignored) and env overrides (`Q_LEDGER_CONFIG_PATH`, `Q_LEDGER_SCOPE_PATH`).

### Fixed
- `load_rows` now counts skipped CSV lines instead of failing silently.

## [0.1.0] - 2026-02-10
### Added
- Initial public baseline for Q-Ledger and Q-Metrics.
- Builder scripts and operational runbook.
- Redacted examples (no raw logs, no IPs, no secrets).
- Security posture documentation (no raw telemetry publication).
