"""
Webhook and API service for the Gigi platform.

This FastAPI application receives notifications from wallet signing
pages, Nomba (fiat) and Transak (crypto) and updates the database
accordingly.  It also exposes a summarisation endpoint used by the
Telegram bot for natural language summarisation.

The webhook verifies incoming payload signatures using the shared
``WEBHOOK_SECRET``, stores each event in a ``WebhookEvent`` table to
prevent duplicate processing, updates ``Transaction`` and ``LedgerEntry``
records and notifies users via the Telegram bot if necessary.  The
actual messaging to Telegram is delegated to the bot code; this module
focuses solely on database state transitions.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import WEBHOOK_SECRET
from .db import async_session, init_db
from . import models
from .openai_util import summarize_text


app = FastAPI(title="Gigi Webhook/API Service")

# Serve the wallet signing pages and other static assets under /static.  The
# directory is resolved relative to this file.
import os
from pathlib import Path
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


async def get_session():
    """Provide a database session as a dependency."""
    async with async_session() as session:
        yield session


def verify_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    """Verify the HMAC signature of the incoming request.

    The signature should be provided in the ``X‑Webhook‑Signature`` header
    and computed as a hex digest of the request body using the shared
    secret from ``WEBHOOK_SECRET``.
    """
    secret = WEBHOOK_SECRET
    if not secret or not signature:
        return False
    computed = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


async def record_event(session, event_id: str, event_type: str, payload: Dict[str, Any]) -> bool:
    """Insert a webhook event into the database.

    Returns True if the event is new and should be processed, False if
    it already exists (idempotent).  In the latter case the caller
    should exit early without repeating side effects.
    """
    existing = await session.get(models.WebhookEvent, {"event_id": event_id})
    if existing:
        return False
    evt = models.WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        payload=json.dumps(payload),
    )
    session.add(evt)
    await session.commit()
    return True


class SignPayload(BaseModel):
    """Schema for wallet signing events from the front‑end."""

    user_id: int
    txHash: str
    amount: float
    token: str
    to: str


@app.on_event("startup")
async def startup() -> None:
    """Initialise the database on startup."""
    await init_db()


@app.post("/ton-webhook")
async def ton_webhook(
    request: Request,
    signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    session=Depends(get_session),
) -> Dict[str, str]:
    """Handle webhooks from the TON wallet signing page."""
    raw = await request.body()
    if not verify_signature(raw, signature):
        raise HTTPException(status_code=401, detail="invalid signature")
    payload = SignPayload.parse_raw(raw)
    # Use txHash as event id for idempotency
    if not await record_event(session, payload.txHash, "ton-webhook", payload.dict()):
        return {"detail": "duplicate"}
    # Update or create transaction record
    # Find transaction by tx_hash or create new one
    from sqlalchemy import select
    result = await session.execute(
        select(models.Transaction).where(models.Transaction.tx_hash == payload.txHash)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        # We don't know the fiat amount yet for a sell flow; assume 0 until
        # the fiat settlement arrives.
        tx = models.Transaction(
            user_id=payload.user_id,
            tx_hash=payload.txHash,
            crypto_amount=payload.amount,
            fiat_amount=0.0,
            token=payload.token,
            chain="TON",
            status=models.OrderStatus.SIGNED,
            tx_type="sell",
        )
        session.add(tx)
    else:
        tx.status = models.OrderStatus.SIGNED
        tx.crypto_amount = payload.amount
    await session.commit()
    # Create ledger entry for the on‑chain transaction
    ledger = models.LedgerEntry(
        user_id=payload.user_id,
        transaction_id=tx.id,
        entry_type=models.LedgerEntryType.DEBIT,
        amount=payload.amount,
        currency=payload.token,
        description="User signed TON transaction",
    )
    session.add(ledger)
    await session.commit()
    return {"detail": "ok"}


@app.post("/evm-webhook")
async def evm_webhook(
    request: Request,
    signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    session=Depends(get_session),
) -> Dict[str, str]:
    """Handle webhooks from the EVM wallet signing page."""
    raw = await request.body()
    if not verify_signature(raw, signature):
        raise HTTPException(status_code=401, detail="invalid signature")
    payload = SignPayload.parse_raw(raw)
    # Use txHash as event id
    if not await record_event(session, payload.txHash, "evm-webhook", payload.dict()):
        return {"detail": "duplicate"}
    from sqlalchemy import select
    result = await session.execute(
        select(models.Transaction).where(models.Transaction.tx_hash == payload.txHash)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        tx = models.Transaction(
            user_id=payload.user_id,
            tx_hash=payload.txHash,
            crypto_amount=payload.amount,
            fiat_amount=0.0,
            token=payload.token,
            chain="EVM",
            status=models.OrderStatus.SIGNED,
            tx_type="sell",
        )
        session.add(tx)
    else:
        tx.status = models.OrderStatus.SIGNED
        tx.crypto_amount = payload.amount
    await session.commit()
    ledger = models.LedgerEntry(
        user_id=payload.user_id,
        transaction_id=tx.id,
        entry_type=models.LedgerEntryType.DEBIT,
        amount=payload.amount,
        currency=payload.token,
        description="User signed EVM transaction",
    )
    session.add(ledger)
    await session.commit()
    return {"detail": "ok"}


@app.post("/solana-webhook")
async def solana_webhook(
    request: Request,
    signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    session=Depends(get_session),
) -> Dict[str, str]:
    """Handle webhooks from the Solana wallet signing page."""
    raw = await request.body()
    if not verify_signature(raw, signature):
        raise HTTPException(status_code=401, detail="invalid signature")
    payload = SignPayload.parse_raw(raw)
    if not await record_event(session, payload.txHash, "solana-webhook", payload.dict()):
        return {"detail": "duplicate"}
    from sqlalchemy import select
    result = await session.execute(
        select(models.Transaction).where(models.Transaction.tx_hash == payload.txHash)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        tx = models.Transaction(
            user_id=payload.user_id,
            tx_hash=payload.txHash,
            crypto_amount=payload.amount,
            fiat_amount=0.0,
            token=payload.token,
            chain="SOLANA",
            status=models.OrderStatus.SIGNED,
            tx_type="sell",
        )
        session.add(tx)
    else:
        tx.status = models.OrderStatus.SIGNED
        tx.crypto_amount = payload.amount
    await session.commit()
    ledger = models.LedgerEntry(
        user_id=payload.user_id,
        transaction_id=tx.id,
        entry_type=models.LedgerEntryType.DEBIT,
        amount=payload.amount,
        currency=payload.token,
        description="User signed Solana transaction",
    )
    session.add(ledger)
    await session.commit()
    return {"detail": "ok"}


class NombaWebhook(BaseModel):
    """Payload from Nomba for payment events.

    The exact schema will depend on Nomba's API; typical fields include
    ``eventId``, ``quoteId``, ``status`` and ``amount``.  We accept
    arbitrary keys and only process those we recognise.
    """

    eventId: str
    quoteId: Optional[str] = None
    status: str
    amount: Optional[float] = None
    user_reference: Optional[int] = None


@app.post("/nomba-webhook")
async def nomba_webhook(
    request: Request,
    signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    session=Depends(get_session),
) -> Dict[str, str]:
    """Handle webhooks from Nomba for payments and payouts."""
    raw = await request.body()
    if not verify_signature(raw, signature):
        raise HTTPException(status_code=401, detail="invalid signature")
    payload = json.loads(raw.decode())
    event_id = payload.get("eventId") or payload.get("id") or ""
    if not event_id:
        raise HTTPException(status_code=400, detail="missing event id")
    if not await record_event(session, event_id, "nomba-webhook", payload):
        return {"detail": "duplicate"}
    quote_id = payload.get("quoteId")
    status = payload.get("status")
    user_ref = payload.get("user_reference")
    amount = float(payload.get("amount") or 0.0)
    if not quote_id:
        return {"detail": "no quote id"}
    # Find transaction by quote_id stored in order_id field
    from sqlalchemy import select
    result = await session.execute(
        select(models.Transaction).where(models.Transaction.order_id == quote_id)
    )
    tx = result.scalar_one_or_none()
    if tx:
        if status.lower() in {"completed", "paid", "success"}:
            tx.status = models.OrderStatus.FUNDED
            tx.fiat_amount = amount
            # Ledger entry credit
            ledger = models.LedgerEntry(
                user_id=tx.user_id,
                transaction_id=tx.id,
                entry_type=models.LedgerEntryType.CREDIT,
                amount=amount,
                currency=tx.token,
                description="Fiat payment received via Nomba",
            )
            session.add(ledger)
        elif status.lower() in {"failed", "rejected"}:
            tx.status = models.OrderStatus.FAILED
        await session.commit()
    return {"detail": "ok"}


class TransakWebhook(BaseModel):
    """Generic Transak webhook payload.

    Transak sends event notifications with an ``eventId`` and an
    ``orderId`` along with the new status.  The payload structure may
    vary depending on the event type.
    """

    eventId: str
    orderId: str
    status: str


@app.post("/transak-webhook")
async def transak_webhook(
    request: Request,
    signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    session=Depends(get_session),
) -> Dict[str, str]:
    """Handle webhooks from Transak for order updates."""
    raw = await request.body()
    if not verify_signature(raw, signature):
        raise HTTPException(status_code=401, detail="invalid signature")
    payload = json.loads(raw.decode())
    event_id = payload.get("eventId") or payload.get("id")
    if not event_id:
        raise HTTPException(status_code=400, detail="missing event id")
    if not await record_event(session, event_id, "transak-webhook", payload):
        return {"detail": "duplicate"}
    order_id = payload.get("orderId") or payload.get("id")
    status = payload.get("status")
    if not order_id:
        return {"detail": "no order id"}
    from sqlalchemy import select
    result = await session.execute(
        select(models.Transaction).where(models.Transaction.order_id == order_id)
    )
    tx = result.scalar_one_or_none()
    if tx:
        # Map Transak statuses to our OrderStatus
        lower = status.lower() if isinstance(status, str) else ""
        if lower in {"payment_pending", "awaiting_payment"}:
            tx.status = models.OrderStatus.PAYMENT_PENDING
        elif lower in {"payment_received", "funds_received", "completed"}:
            tx.status = models.OrderStatus.EXECUTED
        elif lower in {"failed", "cancelled"}:
            tx.status = models.OrderStatus.FAILED
        await session.commit()
    return {"detail": "ok"}


class SummaryRequest(BaseModel):
    text: str


@app.post("/summarise")
async def summarise(req: SummaryRequest) -> Dict[str, str]:
    """Summarise arbitrary text using OpenAI."""
    summary = await summarize_text(req.text)
    return {"summary": summary}


@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Gigi webhook service running"}
