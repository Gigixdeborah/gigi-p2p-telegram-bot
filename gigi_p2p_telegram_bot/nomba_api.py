"""
Integration with the Nomba payments API.

This module provides functions to create quotes and execute fiat payments
via the Nomba REST API. Endpoints and parameters follow Nomba's
documentation. Each call is asynchronous and uses httpx.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import httpx

from .config import NOMBA_API_KEY, NOMBA_BASE_URL

API_BASE_URL = NOMBA_BASE_URL or "https://api.nomba.com"

async def create_fiat_quote(fiat_currency: str, amount: float, direction: str) -> Dict[str, Any]:
    """Request a quote for a fiat transaction."""
    if not NOMBA_API_KEY:
        raise RuntimeError("NOMBA_API_KEY not configured")
    url = f"{API_BASE_URL}/v1/transactions/quotes"
    payload = {
        "currency": fiat_currency,
        "amount": amount,
        "direction": direction,
    }
    headers = {"Authorization": f"Bearer {NOMBA_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

async def execute_fiat_payment(
    user_id: int, quote_id: str, payment_method: str, account_details: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Execute a fiat payment or payout via Nomba."""
    if not NOMBA_API_KEY:
        raise RuntimeError("NOMBA_API_KEY not configured")
    url = f"{API_BASE_URL}/v1/transactions/payments"
    payload: Dict[str, Any] = {
        "quote_id": quote_id,
        "payment_method": payment_method,
        "user_reference": user_id,
    }
    if account_details:
        payload["account_details"] = account_details
    headers = {"Authorization": f"Bearer {NOMBA_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
