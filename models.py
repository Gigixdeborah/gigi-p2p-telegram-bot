from datetime import datetime
import enum

from sqlalchemy import Column, Integer, String, Float, Enum as SAEnum, ForeignKey, DateTime, JSON, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TransactionStatus(enum.Enum):
    INITIATED = "initiated"
    QUOTED = "quoted"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    PAYMENT_PENDING = "payment_pending"
    FUNDED = "funded"
    SIGNED = "signed"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    # backward compatibility aliases still used in existing code paths
    PENDING = "pending"
    PAID = "paid"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    fiat_currency = Column(String(3), default="NGN")
    lang = Column(String(2), default="EN")
    tone = Column(String(20), default="playful")
    ton_wallet = Column(String(100))
    evm_wallet = Column(String(100))
    sol_wallet = Column(String(100))
    kyc_status = Column(String(20), default="not_started")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)
    bank_name = Column(String(50), nullable=False)
    account_number = Column(String(20), nullable=False)
    verified_name = Column(String(100))
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)
    tx_hash = Column(String(100), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    token = Column(String(10), nullable=False)
    chain = Column(String(20), nullable=False)
    status = Column(SAEnum(TransactionStatus, native_enum=False), default=TransactionStatus.INITIATED)
    fiat_amount = Column(Float, nullable=True)
    bybit_order_id = Column(String(100))
    provider = Column(String(20), nullable=True)
    provider_order_id = Column(String(120), nullable=True)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_webhook_provider_event"),)

    id = Column(Integer, primary_key=True)
    provider = Column(String(20), nullable=False)
    event_id = Column(String(200), nullable=False)
    signature = Column(String(255), nullable=True)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), default="received")
    received_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
