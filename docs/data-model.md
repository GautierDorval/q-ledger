# Data model

Ce document est une vue d’ensemble lisible par humain. La référence machine‑first est dans :

- `schemas/q-ledger.schema.json`
- `schemas/q-metrics.schema.json`

## Q‑Ledger

Un fichier Q‑Ledger est un snapshot append‑only, chaîné par hash.

Champs racine (résumé) :

- `ledger_version` : version du format (ex. `1.1`)
- `ledger_sequence` : compteur monotone
- `site` : base URL du site observé
- `generated_utc` : timestamp ISO 8601
- `method` : méta de génération (pipeline, version, paramètres)
- `export_window` : fenêtre d’observation (ex. `manual`)
- `input_stats` : statistiques d’ingestion (lignes CSV total/chargées/ignorées)
- `sessions_inferred[]` : sessions inférées à partir des logs
- `integrity` : chaînage (`previous_ledger_hash_sha256`) + hash canonique

### sessions_inferred[]

Chaque session est un artefact **dérivé** :

- `session_id` : identifiant court
- `start_utc`, `end_utc` : fenêtre de session
- `client_fingerprint_hash` : hash salé (pseudonyme, non‑réversible)
- `hit_count` : nombre de hits dans la session
- `path[]` : chemins observés (normalisés)
- `signals[]` : signaux d’inférence de session (ex. `yaml_preference`)
- `confidence` : score de confiance (0.0 à 1.0)
- `confidence_label` : `low | medium | high`
- `agent_classification` : résumé explicite de la classification (`confidence_level`, `primary_signal`)

## Q‑Metrics

Un fichier Q‑Metrics est un dérivé agrégé de Q‑Ledger, destiné à être consommé par des agents et des auditeurs.

Champs principaux :

- `metrics.entry_compliance_rate`
- `metrics.constraint_touch_rate`
- `metrics.escape_rate`
- `metrics.sequence_fidelity`

Champs de traçabilité :

- `canonical` : URL canonique du fichier Q‑Metrics
- `derived_from[]` : source(s) Q‑Ledger
- `traceability` : URLs de référence (Q‑Ledger, Q‑Metrics YAML, protocole, changelog, etc.)
- `disclosure_token` : marqueur d’intention (voir `docs/disclosure-token.md`)
