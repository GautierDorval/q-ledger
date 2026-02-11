# Modèle de données (résumé)

## q-ledger (ledger_version 1.1)

Champs clés (vue d’ensemble) :

- `ledger_version` : version du format
- `ledger_sequence` : compteur monotone (persisté dans `state/ledger-state.json`)
- `generated_utc` : horodatage de génération
- `sessions_inferred[]` : sessions inférées à partir des logs filtrés
  - `session_id` : identifiant déterministe (hash) basé sur le fingerprint + fenêtre temporelle
  - `window_utc.start/end`
  - `client_fingerprint_hash` : hash SHA‑256 de `ip|ua|salt` (tronqué)
  - `path[]` : chemins observés
  - `path_categories[]` : catégories issues de `config/governance_scope.json`
  - `signals[]` : signaux faibles (yaml_accessed, path_revisited, …)
  - `agent_classification` : hypothèse non‑probante

- `integrity.content_hash_sha256` : hash SHA‑256 du ledger canonique (JSON trié)
- `integrity.previous_ledger_hash_sha256` : hash précédent (chaînage)

## q-metrics (schemaVersion 0.1.0)

- `purpose` et `non_normative_notice` : garde‑fous explicites
- `metrics.counts` : compteurs dérivés (sessions, entrypoint first, constraints touched…)
- `metrics.rates` : taux dérivés (entry compliance, escape rate, sequence fidelity…)
- `traceability` : liens vers Q‑Ledger, Q‑Attest, changelog

> Objectif : publier des métriques **descriptives** qui rendent l’observabilité exploitable, sans prétendre à une conformité.
