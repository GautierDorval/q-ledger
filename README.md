# Q‑Ledger

> **Q‑Ledger** est un *observational ledger* (registre d’observabilité) dérivé de logs HTTP (ex: Cloudflare Log Search) afin de rendre **mesurable, reproductible et contestable** le comportement de lecture des artefacts de gouvernance publiés sur un site (fichiers `/.well-known/*`, manifeste, contraintes, ontologie, etc.).

Ce dépôt contient une **implémentation de référence** en Python (mode “pipeline manuel”) qui :

- ingère un export CSV Cloudflare,
- infère des *sessions* par fingerprint pseudonymisé (IP + UA + sel),
- produit un ledger chaîné (hash SHA‑256 + `previous_ledger_hash_sha256`) en **JSON + YAML**,
- génère des métriques dérivées :
  - `out/metrics.md` (legacy),
  - `out/q-metrics.json` + `out/q-metrics.yml` (Q‑Metrics, non‑normatif).

## Ce que Q‑Ledger n’est pas

- **Pas une preuve d’identité** : aucune revendication “ce modèle = X”.  
- **Pas une preuve cryptographique** : pas d’attestation sans un protocole séparé (voir `q-attest`).
- **Pas un mécanisme d’autorisation** : ce n’est *pas* un “permis” de réponse, mais de l’observabilité.

## Démarrage rapide (manuel)

### 1) Pré‑requis

- Python 3.10+ (3.11 conseillé)
- `pip install -r requirements.txt`
- Définir un sel **secret** :

```bash
export Q_LEDGER_SALT="une_chaine_aleatoire_longue"
```

> ⚠️ **Ne jamais committer** ce sel. Rotater si compromis.

### 2) Export Cloudflare

- Cloudflare Log Search
- Fenêtre : last 24h (quotidien) ou last 48h
- Export : CSV  
- Placer le fichier dans `input/cloudflare_logs.csv`

### 3) Construire le ledger + métriques

```bash
python scripts/build_ledger.py
python scripts/metrics.py out/q-ledger.json out/metrics.md
python scripts/summary_7d.py  # optionnel
```

### 4) Publier (option WordPress “Virtual Files”)

Le workflow fourni inclut des scripts PowerShell (`scripts/publish.ps1`) pour copier-coller le contenu vers :

- `/.well-known/q-ledger.json`
- `/.well-known/q-ledger.yml`
- `/.well-known/q-metrics.json`
- `/.well-known/q-metrics.yml`

Voir `RUNBOOK.md`.

## Sécurité & vie privée (important)

- **NE PAS publier** :
  - `input/` et `exports/` (IPs + User‑Agents),
  - `cle.txt` / `.env` / tokens / clés,
  - un `.venv/` versionné.
- Le ledger dérivé contient un `client_fingerprint_hash` **pseudonymisé**.  
  Même pseudonymisé, cela peut rester “donnée personnelle” selon le contexte : publier en connaissance de cause.

## Structure recommandée des dépôts

Pour éviter les erreurs :

- `q-ledger` (code + spec + docs) → public
- `q-ledger-archive` (uniquement sorties dérivées : q-ledger + q-metrics) → public *ou* privé selon vos contraintes
- logs bruts → **privé / local uniquement**

## Licence

Choisir une licence (MIT / Apache‑2.0 / …) avant publication.

---

### English (one‑liner)

Q‑Ledger is a log‑derived observational governance ledger (JSON+YAML) with chained integrity hashes and non‑normative derived metrics (Q‑Metrics).
