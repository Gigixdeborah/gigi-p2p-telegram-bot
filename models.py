from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Enum as SAEnum, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

# ✅ Safe Enum for transaction status
class TransactionStatus(enum.Enum):
    PENDING = "pending"
    SIGNED = "signed"
    PAID = "paid"
    FAILED = "failed"
    SELL_FAILED = "sell_failed"

# ✅ User model
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ✅ Bank account model
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

# ✅ Transaction model
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)
    tx_hash = Column(String(100), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    token = Column(String(10), nullable=False)
    chain = Column(String(20), nullable=False)
    status = Column(SAEnum(TransactionStatus), default=TransactionStatus.PENDING)
    fiat_amount = Column(Float, nullable=True)
    bybit_order_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
