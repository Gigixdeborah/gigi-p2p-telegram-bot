import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import ASYNC_DATABASE_URL, WEBHOOK_SECRET, validate_required_env
from models import Base, Transaction, TransactionStatus, WebhookEvent

logger = logging.getLogger("gigi.webhook")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="GigiP2Bot Webhooks")
engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@app.on_event("startup")
async def startup() -> None:
    validate_required_env("webhook")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _read_signature(headers: dict[str, str]) -> str:
    for key in ("x-webhook-signature", "x-signature", "x-nomba-signature", "x-transak-signature"):
        if headers.get(key):
            return headers[key]
    return ""


def verify_signature(raw_body: bytes, signature: str) -> bool:
    if not WEBHOOK_SECRET:
        return False
    expected = hmac.new(WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def get_event_id(payload: dict[str, Any], provider: str, fallback_hash: str) -> str:
    return (
        str(payload.get("event_id") or payload.get("eventId") or payload.get("id") or payload.get("reference")
            or payload.get("order_id") or payload.get("orderId") or payload.get("txHash") or payload.get("tx_hash")
            or payload.get("transactionId") or f"{provider}:{fallback_hash}")
    )


def _normalize_status(raw: str | None) -> TransactionStatus | None:
    if not raw:
        return None
    value = raw.strip().lower()
    mapping = {
        "pending": TransactionStatus.PAYMENT_PENDING,
        "processing": TransactionStatus.EXECUTING,
        "paid": TransactionStatus.FUNDED,
        "success": TransactionStatus.COMPLETED,
        "completed": TransactionStatus.COMPLETED,
        "failed": TransactionStatus.FAILED,
        "cancelled": TransactionStatus.CANCELLED,
        "canceled": TransactionStatus.CANCELLED,
        "refunded": TransactionStatus.REFUNDED,
        "signed": TransactionStatus.SIGNED,
    }
    return mapping.get(value)


async def process_provider_webhook(provider: str, request: Request, signature: str) -> JSONResponse:
    raw_body = await request.body()
    if not verify_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid json") from exc

    fallback_hash = hashlib.sha256(raw_body).hexdigest()
    event_id = get_event_id(payload, provider, fallback_hash)

    async with SessionLocal() as db:
        existing = await db.execute(
            select(WebhookEvent).where(
                WebhookEvent.provider == provider,
                WebhookEvent.event_id == event_id,
            )
        )
        if existing.scalar_one_or_none():
            logger.info("duplicate webhook ignored provider=%s event_id=%s", provider, event_id)
            return JSONResponse({"status": "duplicate_ignored", "event_id": event_id})

        event = WebhookEvent(
            provider=provider,
            event_id=event_id,
            signature=signature,
            payload=payload,
            status="received",
        )
        db.add(event)
        await db.flush()

        tx_hash = payload.get("tx_hash") or payload.get("txHash")
        provider_order_id = str(payload.get("order_id") or payload.get("orderId") or payload.get("reference") or "")
        status = _normalize_status(payload.get("status") or payload.get("event"))

        tx_obj = None
        if tx_hash:
            res = await db.execute(select(Transaction).where(Transaction.tx_hash == tx_hash))
            tx_obj = res.scalar_one_or_none()
        elif provider_order_id:
            res = await db.execute(select(Transaction).where(Transaction.provider_order_id == provider_order_id))
            tx_obj = res.scalar_one_or_none()

        if tx_obj:
            tx_obj.provider = provider
            if provider_order_id:
                tx_obj.provider_order_id = provider_order_id
            if status:
                tx_obj.status = status
            if status == TransactionStatus.FAILED:
                tx_obj.failure_reason = str(payload.get("reason") or payload.get("message") or "provider failure")

        event.status = "processed"
        event.processed_at = datetime.utcnow()
        await db.commit()

    return JSONResponse({"status": "ok", "event_id": event_id})



@app.post("/summarize")
async def summarize(payload: dict[str, str]) -> dict[str, str]:
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    summary = text if len(text) <= 180 else text[:177] + "..."
    return {"summary": summary}


@app.post("/nomba-webhook")
async def nomba_webhook(request: Request, x_webhook_signature: str | None = Header(default=None)) -> JSONResponse:
    signature = x_webhook_signature or _read_signature(dict(request.headers))
    return await process_provider_webhook("nomba", request, signature)


@app.post("/transak-webhook")
async def transak_webhook(request: Request, x_webhook_signature: str | None = Header(default=None)) -> JSONResponse:
    signature = x_webhook_signature or _read_signature(dict(request.headers))
    return await process_provider_webhook("transak", request, signature)


@app.post("/ton-webhook")
async def ton_webhook(request: Request, x_webhook_signature: str | None = Header(default=None)) -> JSONResponse:
    signature = x_webhook_signature or _read_signature(dict(request.headers))
    return await process_provider_webhook("ton", request, signature)


@app.post("/evm-webhook")
async def evm_webhook(request: Request, x_webhook_signature: str | None = Header(default=None)) -> JSONResponse:
    signature = x_webhook_signature or _read_signature(dict(request.headers))
    return await process_provider_webhook("evm", request, signature)


@app.post("/solana-webhook")
async def solana_webhook(request: Request, x_webhook_signature: str | None = Header(default=None)) -> JSONResponse:
    signature = x_webhook_signature or _read_signature(dict(request.headers))
    return await process_provider_webhook("solana", request, signature)
