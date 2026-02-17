# Publication / Ops

## Pipeline manuel (référence)

Voir `RUNBOOK.md`.

Étapes :

1. Export Cloudflare Log Search (CSV)
2. Copier vers `input/cloudflare_logs.csv`
3. `python scripts/build_ledger.py`
4. `python scripts/metrics.py out/q-ledger.json out/metrics.md` (génère aussi `out/q-metrics.json` et `out/q-metrics.yml` par défaut)
5. Archiver (optionnel) via `scripts/archive.ps1`
6. Publier (WordPress Virtual Files) via `scripts/publish.ps1`
7. Vérifier automatiquement la publication : `scripts/verify-publication.ps1` (compare les hashes canoniques)

## Automatisation (idées)

- Exécuter la génération quotidienne via un runner (GitHub Actions / cron) **si** l’export Cloudflare est automatisable.
- Publier les sorties dérivées dans un repo `q-ledger-archive` (commit + tag) pour créer un historique transparent.
- Ajouter un petit “dashboard” statique (HTML) qui lit `/.well-known/q-metrics.json` et affiche les tendances.
