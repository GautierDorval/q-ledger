# Privacy & threat model

## Données brutes (à ne pas publier)

Les exports Cloudflare (`input/`, `exports/`) contiennent :

- IP client
- User‑Agent
- Horodatage
- Path / host
- RayID (selon export)

➡️ Ces données peuvent être personnelles et/ou sensibles. Elles doivent rester privées (ou anonymisées de façon robuste).

## Données dérivées (ledger)

Le ledger remplace IP+UA par un `client_fingerprint_hash = sha256(ip|ua|salt)`.

- Si le sel est secret et non publié, l’inversion est impraticable.
- Le hash reste **pseudonyme** (traçable dans le temps) : selon les juridictions, cela peut encore être “donnée personnelle”.

## Limites / attaques

- **Aucune preuve d’identité** : un UA peut être usurpé.
- **Biais d’observabilité** : on mesure seulement ce qui est dans la fenêtre exportée et dans le scope.
- **Échantillonnage / filtrage** : les règles Cloudflare et le filtre “governance_paths” influencent fortement les résultats.

## Bonnes pratiques

- Rotater `Q_LEDGER_SALT` si fuite.
- Publier uniquement `/.well-known/q-ledger.*` + `/.well-known/q-metrics.*`.
- Éviter d’archiver publiquement les logs bruts.
- Documenter la méthode et les limites (voir README).
