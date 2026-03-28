"""
Database models for the production Gigi crypto platform.

The models defined here extend and generalise the existing
`gigi-webhook` and `gigi-p2p-telegram-bot` schemas to accommodate
additional functionality required for a full buy/sell execution
platform.  Notable changes include:

* `KYCStatus` – track whether a user has completed identity
  verification via our KYC provider (Transak).
* `OrderStatus` – a finer grained state machine for transaction
  lifecycles beyond simple "pending/signed/paid".  States include
  initiation, quoting, funding, execution, completion and failure.
* `LedgerEntry` – an internal general-purpose ledger capturing
  debits and credits across both fiat and crypto rails.  This
  facilitates auditability and reporting for the admin dashboard.

All models share timestamps and use SQLAlchemy's declarative base.
These models are compatible with both synchronous and asynchronous
SQLAlchemy sessions; migration tooling such as Alembic can be used
to evolve the schema.  When adding new columns ensure that
non-null constraints are respected via sensible defaults.
"""

from __future__ import annotations

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class KYCStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class OrderStatus(enum.Enum):
    INITIATED = "initiated"
    QUOTED = "quoted"
    PAYMENT_PENDING = "payment_pending"
    SIGNED = "signed"
    FUNDED = "funded"
    EXECUTED = "executed"
    COMPLETED = "completed"
    FAILED = "failed"

class LedgerEntryType(enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    fiat_currency = Column(String(3), default="NGN")
    lang = Column(String(2), default="EN")
    tone = Column(String(20), default="playful")
    ton_wallet = Column(String(100), nullable=True)
    evm_wallet = Column(String(100), nullable=True)
    sol_wallet = Column(String(100), nullable=True)
    kyc_status = Column(SAEnum(KYCStatus), default=KYCStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tx_hash = Column(String(100), unique=True, nullable=True)
    order_id = Column(String(100), unique=True, nullable=True)
    crypto_amount = Column(Float, nullable=False)
    fiat_amount = Column(Float, nullable=False)
    token = Column(String(10), nullable=False)
    chain = Column(String(20), nullable=False)
    status = Column(SAEnum(OrderStatus), default=OrderStatus.INITIATED, nullable=False)
    tx_type = Column(String(10), default="buy")
    fee_usd = Column(Float, default=0.15)
    payout_status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    entry_type = Column(SAEnum(LedgerEntryType), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    description = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id = Column(Integer, primary_key=True)
    event_id = Column(String(100), unique=True, nullable=False)
    event_type = Column(String(50), nullable=True)
    payload = Column(String, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow)

__all__ = [
    "Base",
    "User",
    "Transaction",
    "LedgerEntry",
    "KYCStatus",
    "OrderStatus",
    "LedgerEntryType",
    "WebhookEvent",
]
