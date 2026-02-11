# Roadmap (proposition)

## 1) Stabiliser le format
- Publier un JSON Schema pour `q-ledger` et `q-metrics`
- Versionner explicitement (`ledger_version`, `schemaVersion`)

## 2) Séparer observation vs attestation
- `q-ledger` : observation (log‑derived)
- `q-attest` : attestation cryptographique (opt‑in) quand applicable

## 3) Dashboard lisible
- Page “Q‑Ledger” (humains) + liens vers `/.well-known/*`
- Page “Q‑Metrics” (graphes simples, tendances 7d)

## 4) Standardisation
- Définir un “minimum viable governance surface” (entrypoint, policy, constraints, ontology)
- Documenter des patterns attendus et ce qu’ils signifient (sans les confondre avec de la conformité)
