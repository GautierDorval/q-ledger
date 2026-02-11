# Security

## Reporting

If you discover a security issue, do **not** open a public issue with sensitive details.
Use a private channel (email / DM) agreed by the maintainer.

## Sensitive material

This project is designed to process raw HTTP logs. Treat the following as sensitive:

- raw Cloudflare exports (IP, User‑Agent),
- salts / tokens / keys,
- any output that could re-identify individuals.

Default `.gitignore` is configured to avoid committing those files.
