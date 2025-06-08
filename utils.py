import asyncio
from typing import Optional
import logging
import os
import json

try:
    import base58
    b58decode = base58.b58decode
except Exception:  # fallback minimal decoder if base58 is unavailable
    _ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

    def b58decode(value: str) -> bytes:
        num = 0
        for char in value:
            num *= 58
            if char not in _ALPHABET:
                raise ValueError("Invalid base58 character")
            num += _ALPHABET.index(char)
        return num.to_bytes((num.bit_length() + 7) // 8, "big")

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

# General JSON helpers
def load_json(path: str, default):
    """Load JSON data from *path* or return *default* if missing."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for {path}: {e}")
        return default


def save_json(path: str, data) -> None:
    """Write *data* as JSON to *path*, creating directories if needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ✅ Get crypto price from Bybit + fallback to CoinGecko
async def fetch_crypto_rates(token: str) -> Optional[float]:
    import requests
    apis = [
        f"https://api.bybit.com/v2/public/tickers?symbol={token.upper()}USDT",
        f"https://api.coingecko.com/api/v3/simple/price?ids={token.lower()}&vs_currencies=usd"
    ]
    for api in apis:
        try:
            response = requests.get(api, timeout=5)
            data = response.json()
            if api.startswith("https://api.bybit"):
                return float(data["result"][0]["last_price"])
            elif api.startswith("https://api.coingecko"):
                return float(data[token.lower()]["usd"])
        except Exception as e:
            logger.warning(f"fetch_crypto_rates error for {token}: {e}")
            continue
    return None

# ✅ Get fiat conversion rate (USD → NGN, etc.)
async def fetch_fiat_rate(fiat: str) -> float:
    import requests
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        data = response.json()
        return data["rates"].get(fiat.upper(), 1.0)
    except Exception as e:
        logger.warning(f"fetch_fiat_rate error for {fiat}: {e}")
        return 1.0

# ✅ Check TON wallet balance via Toncenter
async def fetch_ton_balance(address: str) -> Optional[float]:
    import requests
    try:
        response = requests.get(
            f"https://toncenter.com/api/v2/getAddressBalance?address={address}",
            timeout=5,
        )
        data = response.json()
        return float(data["result"]) / 1e9 if "result" in data else None
    except Exception as e:
        logger.warning(f"fetch_ton_balance error: {e}")
        return None

# ✅ Address validator for TON, EVM, Solana
def validate_address(address: str, chain: str) -> bool:
    if not address or not isinstance(address, str):
        return False

    chain = chain.upper()
    if chain == "TON":
        return 40 <= len(address) <= 66 and address.startswith("UQ") and "_" in address
    elif chain == "EVM":
        return address.startswith("0x") and len(address) == 42 and all(c in "0123456789abcdefABCDEF" for c in address[2:])
    elif chain == "SOLANA":
        try:
            decoded = b58decode(address)
            return 32 <= len(decoded) <= 44
        except Exception:
            return False
    return False
