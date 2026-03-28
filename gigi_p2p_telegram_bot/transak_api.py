"""
Integration with the Transak API for crypto purchase and sale.

This module wraps common Transak operations such as quoting prices,
creating orders, checking order status and retrieving KYC status.
"""

from __future__ import annotations

import httpx
from typing import Dict, Any, Optional

from .config import TRANSAK_API_KEY, TRANSAK_BASE_URL

API_BASE_URL = TRANSAK_BASE_URL or "https://api.transak.com/api/v2"

async def get_crypto_quote(
    crypto_currency: str,
    fiat_currency: str,
    amount: float,
    direction: str,
) -> Dict[str, Any]:
    """Fetch a price quote from Transak."""
    if not TRANSAK_API_KEY:
        raise RuntimeError("TRANSAK_API_KEY not configured")
    params: Dict[str, Any] = {
        "cryptoCurrencyCode": crypto_currency,
        "fiatCurrency": fiat_currency,
        "isBuyOrSell": direction.upper(),
    }
    if direction.lower() == "buy":
        params["fiatAmount"] = amount
    else:
        params["cryptoAmount"] = amount
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE_URL}/prices", params=params, headers={"apiKey": TRANSAK_API_KEY}, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
    return {
        "quote_id": data.get("quoteId") or data.get("id") or "",
        "crypto_amount": float(data.get("cryptoAmount") or amount),
        "fiat_amount": float(data.get("fiatAmount") or amount),
        "rate": float(data.get("conversionRate") or data.get("price") or 0.0),
    }

async def create_order(
    user_id: int,
    quote_id: str,
    wallet_address: str,
    network: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an order on Transak for a quoted price."""
    if not TRANSAK_API_KEY:
        raise RuntimeError("TRANSAK_API_KEY not configured")
    payload: Dict[str, Any] = {
        "quoteId": quote_id,
        "walletAddress": wallet_address,
    }
    if network:
        payload["network"] = network
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE_URL}/orders",
            json=payload,
            headers={"apiKey": TRANSAK_API_KEY, "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    return {"order_id": data.get("orderId") or data.get("id"), "status": data.get("status")}

async def check_order_status(order_id: str) -> Dict[str, Any]:
    """Retrieve the current status of an existing order."""
    if not TRANSAK_API_KEY:
        raise RuntimeError("TRANSAK_API_KEY not configured")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE_URL}/orders/{order_id}", headers={"apiKey": TRANSAK_API_KEY}, timeout=30
        )
        resp.raise_for_status()
    return resp.json()

async def get_kyc_status(user_id: int) -> Dict[str, Any]:
    """Retrieve KYC status for the given user."""
    if not TRANSAK_API_KEY:
        raise RuntimeError("TRANSAK_API_KEY not configured")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE_URL}/users/{user_id}/kyc", headers={"apiKey": TRANSAK_API_KEY}, timeout=30
        )
        resp.raise_for_status()
    return resp.json()
