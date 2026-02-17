# Disclosure token

The `disclosure_token` field in `q-metrics.json` is an **intent marker**.

- It is **not** a secret.
- It is **not** authentication.
- It is **not** proof of identity or compliance.

Its purpose is to make it explicit that the publisher intentionally exposes Q-Ledger / Q-Metrics artifacts as part of a governed disclosure surface (for crawlers, auditors, and automated consumers).

## Defaults and configuration

You can set the token in two ways (highest priority first):

1. `Q_LEDGER_DISCLOSURE_TOKEN` environment variable
2. `q_metrics.disclosure_token` in your config JSON

If neither is set, the default is:

- `Q-LEDGER-DISCLOSED`

Recommended practice: choose a stable, organization-specific token, e.g. `ACME-QLEDGER-GOVERNED`, and treat it like a public identifier.
