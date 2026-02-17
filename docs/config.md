# Configuration

Q-Ledger uses JSON configs under `config/`.

## Recommended workflow

1. Copy templates:

- `config/config.example.json` → `config/config.local.json`
- `config/governance_scope.example.json` → `config/governance_scope.local.json`

2. Edit `config/config.local.json`:

- `site`
- `input.csv_path`
- `output.*` paths

3. Set required env var:

- `Q_LEDGER_SALT` (or change `fingerprint_salt_env` in config)

`.local` files are gitignored by default.

## Config resolution order

Build (`scripts/build_ledger.py`) and metrics (`scripts/metrics.py`) resolve config paths in this order:

1. CLI overrides where supported (`--config`, `--scope`)
2. Environment: `Q_LEDGER_CONFIG_PATH`, `Q_LEDGER_SCOPE_PATH`
3. Local files: `config/*.local.json`
4. Committed demo defaults: `config/config.json`, `config/governance_scope.json`
5. Templates: `config/config.example.json`, `config/governance_scope.example.json`
