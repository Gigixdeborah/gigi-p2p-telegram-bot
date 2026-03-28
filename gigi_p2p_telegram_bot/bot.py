"""
Telegram bot for the Gigi crypto platform.

This script uses python‑telegram‑bot v20+ to implement a simple
conversation flow for buying and selling cryptocurrency.  It relies
on Transak for price quotes and order execution, Nomba for fiat
collection/payout and OpenAI for natural language fallbacks.  The
database is managed via SQLAlchemy with async support.

To run locally, ensure that the required environment variables are
set (see config.py) and install dependencies from requirements.txt.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional, Tuple

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from sqlalchemy import select

from .config import (
    TELEGRAM_BOT_TOKEN,
    ADMIN_CHAT_ID,
    TWA_BASE_URL,
)
from .db import async_session, init_db
from . import models
from .nomba_api import create_fiat_quote, execute_fiat_payment
from .transak_api import get_crypto_quote, create_order, check_order_status, get_kyc_status
from .quote_engine import get_rate
from .openai_util import ask_openai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_user(session, telegram_id: int) -> models.User:
    """Retrieve or create a user record based on Telegram id."""
    result = await session.execute(
        select(models.User).where(models.User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = models.User(telegram_id=telegram_id)
        session.add(user)
        await session.commit()
    return user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with async_session() as session:
        await get_user(session, update.effective_user.id)
    await update.message.reply_text(
        "Welcome to Gigi! Use /kyc to verify your account, /buy or /sell to trade, and /order <id> to check status."
    )


async def kyc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check KYC status via Transak and update the user record."""
    user_id = update.effective_user.id
    async with async_session() as session:
        user = await get_user(session, user_id)
        try:
            status_resp = await get_kyc_status(user_id)
            status_str = status_resp.get("status", "pending").lower()
            if status_str == "approved":
                user.kyc_status = models.KYCStatus.APPROVED
                reply = "✅ Your KYC is approved! You can now trade."
            elif status_str == "rejected":
                user.kyc_status = models.KYCStatus.REJECTED
                reply = "❌ Your KYC has been rejected. Please contact support."
            else:
                user.kyc_status = models.KYCStatus.PENDING
                reply = "🕒 Your KYC is pending. Please complete verification with our provider."
            await session.commit()
        except Exception as exc:
            logger.error("KYC check failed: %s", exc)
            reply = "Failed to retrieve KYC status. Please try again later."
    await update.message.reply_text(reply)


async def parse_trade_args(args: Tuple[str, ...]) -> Tuple[str, float]:
    """Parse token and amount from command arguments."""
    if len(args) < 2:
        raise ValueError("Usage: /buy TOKEN AMOUNT or /sell TOKEN AMOUNT")
    token = args[0].upper()
    try:
        amount = float(args[1])
    except ValueError as e:
        raise ValueError("Amount must be a number") from e
    return token, amount


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /buy command. Fetch a price quote and ask for confirmation."""
    user_id = update.effective_user.id
    try:
        token, amount = await parse_trade_args(tuple(context.args))
    except ValueError as err:
        await update.message.reply_text(str(err))
        return
    async with async_session() as session:
        user = await get_user(session, user_id)
        if user.kyc_status != models.KYCStatus.APPROVED:
            await update.message.reply_text("Please complete KYC verification with /kyc before trading.")
            return
    fiat_currency = "USD"
    try:
        quote = await get_crypto_quote(token, fiat_currency, amount=amount, direction="buy")
    except Exception as exc:
        logger.error("Quote retrieval failed: %s", exc)
        await update.message.reply_text("Sorry, I couldn't fetch a quote right now. Please try again later.")
        return
    fiat_amount = quote.get("fiat_amount")
    quote_id = quote.get("quote_id")
    rate = quote.get("rate")
    # Store a transaction with status QUOTED
    async with async_session() as session:
        user = await get_user(session, user_id)
        tx = models.Transaction(
            user_id=user.id,
            order_id=quote_id,
            crypto_amount=amount,
            fiat_amount=fiat_amount,
            token=token,
            chain="",  # unknown until wallet selection
            status=models.OrderStatus.QUOTED,
            tx_type="buy",
        )
        session.add(tx)
        await session.commit()
        tx_id = tx.id
    # Ask user to confirm purchase
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=f"Buy {amount} {token} for {fiat_amount:.2f} {fiat_currency}",
                callback_data=f"confirm_buy:{tx_id}:{quote_id}:{token}:{amount}:{fiat_amount}",
            )
        ],
        [InlineKeyboardButton(text="Cancel", callback_data=f"cancel:{tx_id}")],
    ])
    await update.message.reply_text(
        f"💱 Quote: {amount} {token} = {fiat_amount:.2f} {fiat_currency} (Rate: {rate})\n"
        "Please confirm to proceed.",
        reply_markup=keyboard,
    )


async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sell command.  This flow requires the user to sign a transaction.
    We fetch a quote and then send the user to the wallet signing page.
    """
    user_id = update.effective_user.id
    try:
        token, amount = await parse_trade_args(tuple(context.args))
    except ValueError as err:
        await update.message.reply_text(str(err))
        return
    async with async_session() as session:
        user = await get_user(session, user_id)
        if user.kyc_status != models.KYCStatus.APPROVED:
            await update.message.reply_text("Please complete KYC verification with /kyc before trading.")
            return
    fiat_currency = "USD"
    try:
        quote = await get_crypto_quote(token, fiat_currency, amount=amount, direction="sell")
    except Exception as exc:
        logger.error("Quote retrieval failed: %s", exc)
        await update.message.reply_text("Sorry, I couldn't fetch a quote right now. Please try again later.")
        return
    fiat_amount = quote.get("fiat_amount")
    quote_id = quote.get("quote_id")
    rate = quote.get("rate")
    # Save transaction record with status QUOTED
    async with async_session() as session:
        user = await get_user(session, user_id)
        tx = models.Transaction(
            user_id=user.id,
            order_id=quote_id,
            crypto_amount=amount,
            fiat_amount=fiat_amount,
            token=token,
            chain="",  # we will fill after sign
            status=models.OrderStatus.QUOTED,
            tx_type="sell",
        )
        session.add(tx)
        await session.commit()
        tx_id = tx.id
    # Provide URL to multi‑sign page with query parameters.  The page
    # will prompt the user to connect their wallet and sign the
    # transaction on their chosen network.  We supply the user id,
    # recipient (admin wallet), amount and token symbol.
    sign_url = (
        f"{TWA_BASE_URL}/multi-sign.html?user={user_id}&recipient={ADMIN_CHAT_ID}"
        f"&amount={amount}&token={token}"
    )
    await update.message.reply_text(
        f"💱 Quote: Sell {amount} {token} for {fiat_amount:.2f} {fiat_currency} (Rate: {rate})\n"
        "Please sign the transaction using your wallet.\n"
        f"Sign here: {sign_url}",
        disable_web_page_preview=True,
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard callbacks for confirmations."""
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data
    if data.startswith("confirm_buy"):
        _, tx_id, quote_id, token, amount, fiat_amount = data.split(":")
        tx_id_int = int(tx_id)
        amount_f = float(amount)
        fiat_f = float(fiat_amount)
        async with async_session() as session:
            tx = await session.get(models.Transaction, tx_id_int)
            if not tx:
                await query.message.reply_text("Transaction not found.")
                return
            # Create fiat quote on Nomba
            try:
                fiat_quote = await create_fiat_quote(
                    fiat_currency="USD",
                    amount=fiat_f,
                    direction="buy",
                )
            except Exception as exc:
                logger.error("Nomba quote failed: %s", exc)
                await query.message.reply_text("Failed to create a fiat quote. Please try later.")
                return
            quote_id_nomba = fiat_quote.get("quote_id") or fiat_quote.get("id")
            # Create order on Transak
            try:
                order = await create_order(
                    user_id=tx.user_id,
                    quote_id=quote_id,
                    wallet_address=ADMIN_CHAT_ID or "",
                    network=None,
                )
            except Exception as exc:
                logger.error("Transak order failed: %s", exc)
                await query.message.reply_text("Failed to create order. Please try again later.")
                return
            order_id = order.get("order_id")
            # Store the Transak order id for subsequent status updates
            tx.order_id = order_id
            tx.status = models.OrderStatus.PAYMENT_PENDING
            await session.commit()
            await query.message.reply_text(
                f"✅ Your order has been created. Please complete the payment of {fiat_f:.2f} USD via Nomba."
            )
    elif data.startswith("cancel"):
        _, tx_id = data.split(":")
        tx_id_int = int(tx_id)
        async with async_session() as session:
            tx = await session.get(models.Transaction, tx_id_int)
            if tx:
                tx.status = models.OrderStatus.FAILED
                await session.commit()
        await query.message.reply_text("Order cancelled.")


async def order_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /order <id> command to check status."""
    if not context.args:
        await update.message.reply_text("Usage: /order <id>")
        return
    try:
        tx_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Order ID must be a number.")
        return
    async with async_session() as session:
        tx = await session.get(models.Transaction, tx_id)
        if not tx:
            await update.message.reply_text("Order not found.")
            return
        await update.message.reply_text(
            f"Order {tx_id} status: {tx.status.value}\n"
            f"Crypto amount: {tx.crypto_amount}\nFiat amount: {tx.fiat_amount}\nToken: {tx.token}\nType: {tx.tx_type}",
            parse_mode=ParseMode.MARKDOWN,
        )


async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's wallet addresses and provide connect links."""
    async with async_session() as session:
        user = await get_user(session, update.effective_user.id)
    reply = (
        f"Your wallets:\nTON: {user.ton_wallet or 'not set'}\n"
        f"EVM: {user.evm_wallet or 'not set'}\n"
        f"Solana: {user.sol_wallet or 'not set'}\n"
        "Use the link below to connect/resync your wallets."
    )
    # Provide TWA URL for connecting wallets.  This page should update the
    # user's wallet addresses via the webhook.
    connect_url = f"{TWA_BASE_URL}/multi-sign.html?user={update.effective_user.id}"
    await update.message.reply_text(reply + f"\n\nConnect here: {connect_url}")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fallback handler for unrecognised commands and messages."""
    text = update.message.text or ""
    try:
        reply = await ask_openai(text)
    except Exception:
        reply = "I'm sorry, I didn't understand that. Please use /help for available commands."
    await update.message.reply_text(reply)


def main() -> None:
    """Start the Telegram bot."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not configured")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("kyc", kyc))
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("sell", sell))
    application.add_handler(CommandHandler("order", order_status))
    application.add_handler(CommandHandler("wallet", wallet))
    application.add_handler(CallbackQueryHandler(handle_callback))
    # Unknown commands and messages
    application.add_handler(MessageHandler(filters.COMMAND | filters.TEXT, unknown))
    # Initialise DB and run polling
    async def run() -> None:
        await init_db()
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        await application.updater.idle()
    asyncio.run(run())


if __name__ == "__main__":
    main()
