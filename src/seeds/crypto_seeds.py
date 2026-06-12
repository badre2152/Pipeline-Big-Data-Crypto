"""
crypto_seeds.py — Reference Data (Hardcoded)
=============================================
dim_category et dim_platform sont des données statiques.
Elles ne viennent PAS de l'API CoinGecko — c'est intentionnel
pour éviter les rate limits du free tier.

Pour ajouter une crypto : compléter CRYPTO_MAPPING uniquement.
Pour ajouter une catégorie : compléter CATEGORIES + CRYPTO_MAPPING.
"""

from __future__ import annotations

CATEGORIES = [
    {"category_key": 1, "category_name": "Layer 1",    "category_desc": "Base blockchain protocols"},
    {"category_key": 2, "category_name": "Layer 2",    "category_desc": "Scaling and rollup solutions"},
    {"category_key": 3, "category_name": "DeFi",       "category_desc": "Decentralized finance protocols"},
    {"category_key": 4, "category_name": "Stablecoin", "category_desc": "Price-stable assets"},
    {"category_key": 5, "category_name": "Oracle",     "category_desc": "Data feed and oracle protocols"},
    {"category_key": 6, "category_name": "Exchange",   "category_desc": "Centralized and decentralized exchange tokens"},
    {"category_key": 7, "category_name": "Meme",       "category_desc": "Community-driven meme tokens"},
    {"category_key": 8, "category_name": "Other",      "category_desc": "Uncategorized or cross-category"},
]

PLATFORMS = [
    {"platform_key": 1, "platform_name": "Bitcoin",    "blockchain": "Bitcoin"},
    {"platform_key": 2, "platform_name": "Ethereum",   "blockchain": "EVM"},
    {"platform_key": 3, "platform_name": "Solana",     "blockchain": "Solana"},
    {"platform_key": 4, "platform_name": "BNB Chain",  "blockchain": "EVM"},
    {"platform_key": 5, "platform_name": "Avalanche",  "blockchain": "EVM"},
    {"platform_key": 6, "platform_name": "Cardano",    "blockchain": "Cardano"},
    {"platform_key": 7, "platform_name": "Polkadot",   "blockchain": "Substrate"},
    {"platform_key": 8, "platform_name": "Tron",       "blockchain": "Tron"},
    {"platform_key": 9, "platform_name": "Native",     "blockchain": "Own chain"},
]

# Mapping coin_id (CoinGecko) → category_key + platform_key
CRYPTO_MAPPING = {
    # ── Layer 1 ───────────────────────────────────────────────
    "bitcoin":           {"category_key": 1, "platform_key": 1},
    "ethereum":          {"category_key": 1, "platform_key": 2},
    "solana":            {"category_key": 1, "platform_key": 3},
    "cardano":           {"category_key": 1, "platform_key": 6},
    "avalanche-2":       {"category_key": 1, "platform_key": 5},
    "polkadot":          {"category_key": 1, "platform_key": 7},
    "tron":              {"category_key": 1, "platform_key": 8},
    "near":              {"category_key": 1, "platform_key": 9},
    "internet-computer": {"category_key": 1, "platform_key": 9},
    "aptos":             {"category_key": 1, "platform_key": 9},
    "sui":               {"category_key": 1, "platform_key": 9},
    "algorand":          {"category_key": 1, "platform_key": 9},
    "cosmos":            {"category_key": 1, "platform_key": 9},
    "stellar":           {"category_key": 1, "platform_key": 9},
    "monero":            {"category_key": 1, "platform_key": 9},

    # ── Layer 2 ───────────────────────────────────────────────
    "matic-network":     {"category_key": 2, "platform_key": 2},
    "arbitrum":          {"category_key": 2, "platform_key": 2},
    "optimism":          {"category_key": 2, "platform_key": 2},
    "starknet":          {"category_key": 2, "platform_key": 2},
    "immutable-x":       {"category_key": 2, "platform_key": 2},

    # ── Stablecoins ───────────────────────────────────────────
    "tether":            {"category_key": 4, "platform_key": 2},
    "usd-coin":          {"category_key": 4, "platform_key": 2},
    "dai":               {"category_key": 4, "platform_key": 2},
    "true-usd":          {"category_key": 4, "platform_key": 2},
    "binance-usd":       {"category_key": 4, "platform_key": 4},

    # ── DeFi ─────────────────────────────────────────────────
    "uniswap":           {"category_key": 3, "platform_key": 2},
    "aave":              {"category_key": 3, "platform_key": 2},
    "curve-dao-token":   {"category_key": 3, "platform_key": 2},
    "maker":             {"category_key": 3, "platform_key": 2},
    "lido-dao":          {"category_key": 3, "platform_key": 2},
    "pancakeswap-token": {"category_key": 3, "platform_key": 4},

    # ── Oracle ────────────────────────────────────────────────
    "chainlink":         {"category_key": 5, "platform_key": 2},
    "the-graph":         {"category_key": 5, "platform_key": 2},

    # ── Exchange ──────────────────────────────────────────────
    "binancecoin":       {"category_key": 6, "platform_key": 4},
    "crypto-com-chain":  {"category_key": 6, "platform_key": 9},
    "okb":               {"category_key": 6, "platform_key": 9},
    "kucoin-shares":     {"category_key": 6, "platform_key": 9},

    # ── Meme ─────────────────────────────────────────────────
    "dogecoin":          {"category_key": 7, "platform_key": 9},
    "shiba-inu":         {"category_key": 7, "platform_key": 2},
    "pepe":              {"category_key": 7, "platform_key": 2},

    # ── Other ─────────────────────────────────────────────────
    "ripple":            {"category_key": 8, "platform_key": 9},
    "litecoin":          {"category_key": 8, "platform_key": 9},
    "bitcoin-cash":      {"category_key": 8, "platform_key": 9},
    "filecoin":          {"category_key": 8, "platform_key": 9},
    "hedera-hashgraph":  {"category_key": 8, "platform_key": 9},
    "vechain":           {"category_key": 8, "platform_key": 9},
    "theta-token":       {"category_key": 8, "platform_key": 9},
    "the-sandbox":       {"category_key": 8, "platform_key": 2},
    "decentraland":      {"category_key": 8, "platform_key": 2},
}

# Fallback pour les cryptos non mappées
DEFAULT_MAPPING = {"category_key": 8, "platform_key": 9}  # Other / Native


def get_mapping(coin_id: str) -> dict:
    """Retourne le mapping category + platform pour un coin_id donné."""
    return CRYPTO_MAPPING.get(coin_id, DEFAULT_MAPPING)