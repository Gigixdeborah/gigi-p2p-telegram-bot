"""initial production schema

Revision ID: 0001_prod_refactor
Revises: 
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_prod_refactor"
down_revision = None
branch_labels = None
depends_on = None


transaction_status_enum = sa.Enum(
    "initiated",
    "quoted",
    "awaiting_confirmation",
    "payment_pending",
    "funded",
    "signed",
    "executing",
    "completed",
    "failed",
    "cancelled",
    "refunded",
    "pending",
    "paid",
    name="transactionstatus",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("fiat_currency", sa.String(length=3), nullable=True),
        sa.Column("lang", sa.String(length=2), nullable=True),
        sa.Column("tone", sa.String(length=20), nullable=True),
        sa.Column("ton_wallet", sa.String(length=100), nullable=True),
        sa.Column("evm_wallet", sa.String(length=100), nullable=True),
        sa.Column("sol_wallet", sa.String(length=100), nullable=True),
        sa.Column("kyc_status", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.telegram_id"), nullable=False),
        sa.Column("bank_name", sa.String(length=50), nullable=False),
        sa.Column("account_number", sa.String(length=20), nullable=False),
        sa.Column("verified_name", sa.String(length=100), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.telegram_id"), nullable=False),
        sa.Column("tx_hash", sa.String(length=100), nullable=False, unique=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("token", sa.String(length=10), nullable=False),
        sa.Column("chain", sa.String(length=20), nullable=False),
        sa.Column("status", transaction_status_enum, nullable=True),
        sa.Column("fiat_amount", sa.Float(), nullable=True),
        sa.Column("bybit_order_id", sa.String(length=100), nullable=True),
        sa.Column("provider", sa.String(length=20), nullable=True),
        sa.Column("provider_order_id", sa.String(length=120), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("event_id", sa.String(length=200), nullable=False),
        sa.Column("signature", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("provider", "event_id", name="uq_webhook_provider_event"),
    )


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_table("transactions")
    op.drop_table("bank_accounts")
    op.drop_table("users")
