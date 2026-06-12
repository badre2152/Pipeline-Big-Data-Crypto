# ADR 002 — Hardcoded Seed Data pour dim_category et dim_platform

**Date :** 2025-06-09
**Statut :** Accepté

## Contexte

Le Snowflake Schema requiert `dim_category` et `dim_platform`.
Ces données ne sont pas disponibles via l'endpoint `/coins/markets`
du free tier CoinGecko. L'endpoint `/coins/{id}` les fournit mais
nécessite un appel par crypto → rate limit immédiat sur 50 cryptos.

## Décision

`dim_category` et `dim_platform` sont alimentées par des données
**hardcodées** dans `src/seeds/crypto_seeds.py`.

Un mapping manuel `coin_id → category_key + platform_key` est maintenu
dans le même fichier pour les top 50 cryptos.

## Justification

- Zéro appels API supplémentaires → pas de rate limit
- Données de catégorie stables dans le temps (Bitcoin restera Layer 1)
- Pattern reconnu en production sous le nom "reference data" ou "master data"
- Fallback automatique vers `Other/Native` pour les cryptos non mappées

## Conséquences

- Mise à jour manuelle si une nouvelle crypto entre dans le top 50
- Mapping initial couvre les top 50 cryptos par market cap (juin 2025)
- `crypto_seeds.py` doit être mis à jour manuellement si nécessaire