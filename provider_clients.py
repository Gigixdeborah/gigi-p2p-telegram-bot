"""Provider clients for Nomba and Transak.

NOTE: Endpoints are wired through environment variables so dashboards/docs can be aligned
without code changes. Defaults reflect currently public docs patterns but must be verified
against your approved merchant account.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

NOMBA_BASE_URL = os.getenv("NOMBA_BASE_URL", "https://api.nomba.com")
NOMBA_API_KEY = os.getenv("NOMBA_API_KEY", "")
NOMBA_QUOTE_PATH = os.getenv("NOMBA_QUOTE_PATH", "/v1/payments/quote")
NOMBA_PAYMENT_PATH = os.getenv("NOMBA_PAYMENT_PATH", "/v1/payments")

TRANSAK_BASE_URL = os.getenv("TRANSAK_BASE_URL", "https://api.transak.com")
TRANSAK_API_KEY = os.getenv("TRANSAK_API_KEY", "")
TRANSAK_QUOTE_PATH = os.getenv("TRANSAK_QUOTE_PATH", "/api/v2/prices")
TRANSAK_ORDER_PATH = os.getenv("TRANSAK_ORDER_PATH", "/api/v2/orders")
TRANSAK_KYC_PATH = os.getenv("TRANSAK_KYC_PATH", "/api/v2/user/kyc")


async def _call(method: str, base_url: str, path: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.request(method, url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


async def get_nomba_quote(amount: float, fiat: str, crypto: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {NOMBA_API_KEY}", "Content-Type": "application/json"}
    payload = {"amount": amount, "fiat": fiat, "crypto": crypto}
    return await _call("POST", NOMBA_BASE_URL, NOMBA_QUOTE_PATH, headers, payload)


async def create_nomba_payment(reference: str, amount: float, currency: str, customer_id: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {NOMBA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "reference": reference,
        "amount": amount,
        "currency": currency,
        "customerId": customer_id,
    }
    return await _call("POST", NOMBA_BASE_URL, NOMBA_PAYMENT_PATH, headers, payload)


async def get_transak_quote(fiat_amount: float, fiat_currency: str, crypto_currency: str, network: str) -> dict[str, Any]:
    headers = {"api-key": TRANSAK_API_KEY}
    payload = {
        "fiatAmount": fiat_amount,
        "fiatCurrency": fiat_currency,
        "cryptoCurrency": crypto_currency,
        "network": network,
    }
    return await _call("POST", TRANSAK_BASE_URL, TRANSAK_QUOTE_PATH, headers, payload)


async def create_transak_order(wallet_address: str, fiat_amount: float, fiat_currency: str, crypto_currency: str, network: str) -> dict[str, Any]:
    headers = {"api-key": TRANSAK_API_KEY, "Content-Type": "application/json"}
    payload = {
        "walletAddress": wallet_address,
        "fiatAmount": fiat_amount,
        "fiatCurrency": fiat_currency,
        "cryptoCurrency": crypto_currency,
        "network": network,
    }
    return await _call("POST", TRANSAK_BASE_URL, TRANSAK_ORDER_PATH, headers, payload)


async def get_transak_kyc_status(user_id: str) -> dict[str, Any]:
    headers = {"api-key": TRANSAK_API_KEY}
    payload = {"userId": user_id}
    return await _call("POST", TRANSAK_BASE_URL, TRANSAK_KYC_PATH, headers, payload)
