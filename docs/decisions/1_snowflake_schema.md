# ADR 001 — Choix du Snowflake Schema

**Date :** 2025-06-09
**Statut :** Accepté

## Contexte

Le projet nécessite un modèle dimensionnel pour analyser les prix, volumes
et performances des cryptomonnaies dans Snowflake + Tableau.

Trois options étaient disponibles : Star Schema, Snowflake Schema, Galaxy Schema.

## Décision

Nous utilisons un **Snowflake Schema** avec normalisation de `dim_category`
et `dim_platform` hors de `dim_crypto`.

## Justification

- `dim_category` et `dim_platform` sont des données de référence stables
  partagées par `dim_crypto` ET `fact_crypto_prices` directement
- La normalisation élimine la redondance : "Layer 1" stocké une seule fois
- Démontre la maîtrise du dimensional modeling au-delà du Star Schema basique

## Conséquences

- Les requêtes SQL nécessitent des JOINs supplémentaires
- Performance légèrement inférieure au Star Schema sur Tableau
- Compensé par la clarté du modèle et l'absence de redondance