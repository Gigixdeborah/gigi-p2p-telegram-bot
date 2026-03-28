"""
Simple quote engine to fetch crypto prices from Transak and cache them briefly.
"""

import time
from typing import Dict, Tuple, Optional

from .transak_api import get_crypto_quote

# Cache storage: key -> (timestamp, response dict)
_cache: Dict[Tuple[str, str, str], Tuple[float, dict]] = {}
_CACHE_TTL = 30  # seconds


async def get_rate(
    token: str,
    fiat_currency: str = "USD",
    amount: float = 1.0,
    direction: str = "buy",
) -> Optional[float]:
    """Get a rate for a token against a fiat currency via Transak with caching.

    Args:
        token: Symbol of the cryptocurrency (e.g. TON, BTC).
        fiat_currency: ISO code of fiat currency (e.g. USD, NGN).
        amount: Amount of crypto for which to fetch a price (used for quoting).
        direction: "buy" or "sell".

    Returns:
        The conversion rate (fiat per crypto) or None if unavailable.
    """
    key = (token.upper(), fiat_currency.upper(), direction.lower())
    now = time.time()
    # Serve from cache if still valid
    if key in _cache:
        ts, data = _cache[key]
        if now - ts < _CACHE_TTL:
            return float(data.get("rate", 0))
    try:
        quote = await get_crypto_quote(token.upper(), fiat_currency.upper(), amount=amount, direction=direction)
    except Exception:
        return None
    _cache[key] = (now, quote)
    return float(quote.get("rate", 0))
