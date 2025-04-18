import os
import json
import time
import logging
import requests
import re
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import nest_asyncio

# Fix Python 3.12 event loop error
nest_asyncio.apply()

# Load environment variables
load_dotenv()

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Data stores
user_data = {}
user_pending_fiat = {}
user_pending_amount = {}
user_wallets = {}
user_orders = {}
user_signatures = {}

# Constants
TON_RECEIVE_ADDRESS = "UQCMbQomO3XD1FSt7pyfjqj2jBRzyg23myKDtCky_CedKpEH"
TON_CONNECT_URL = (
    "https://t.me/wallet/start?startapp=tonconnect-v2"
    "&manifestUrl=https://gigi-ton-connect-v2.onrender.com/tonconnect-manifest.json"
)
TON_CONNECT_BASE = "https://gigi-ton-connect-v2.onrender.com"

SUPPORTED_FIATS = ["NGN", "GHS", "KES", "USD", "ZAR", "GBP"]
SUPPORTED_CRYPTOS = ["btc", "eth", "usdt", "bnb", "sol", "ton", "ada", "xrp", "dot", "doge"]

# ================= HELPER FUNCTIONS =================

def get_usdt_to_fiat_rate(fiat):
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        r = requests.get(url).json()
        return r['rates'].get(fiat.upper(), None)
    except:
        return None

def get_crypto_price(symbol):
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=spot"
        r = requests.get(url).json()
        tickers = r.get("result", {}).get("list", [])
        for coin in tickers:
            if coin["symbol"] == f"{symbol.upper()}USDT":
                return float(coin["lastPrice"])
        return None
    except:
        return None

def detect_sell_command(text):
    match = re.search(r"(sell|send)\\s+(\\d+(\\.\\d+)?)\\s*(ton)", text.lower())
    if match:
        return {
            "action": "sell",
            "amount": float(match.group(2)),
            "token": match.group(4).upper()
        }
    return None

def generate_ton_sign_link(amount_ton: float):
    amount_nano = int(amount_ton * 1e9)
    return f"{TON_CONNECT_BASE}/sign?amount={amount_nano}&to={TON_RECEIVE_ADDRESS}"

# ================= BOT COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = update.message.chat_id
        logging.info(f"📢 /start received from {uid}")

        keyboard = [
            [InlineKeyboardButton("🔗 Connect Wallet", url=TON_CONNECT_URL)],
            [InlineKeyboardButton("💵 Buy Crypto", callback_data="buy_crypto"),
             InlineKeyboardButton("💸 Sell Crypto", callback_data="sell_crypto")],
            [InlineKeyboardButton("💰 Select Fiat", callback_data="select_fiat")],
            [InlineKeyboardButton("ℹ Help", callback_data="help"),
             InlineKeyboardButton("📝 Sign", callback_data="sign")],
            [InlineKeyboardButton("📦 View Wallet", callback_data="view_wallet"),
             InlineKeyboardButton("📋 Order History", callback_data="history")]
        ]

        await update.message.reply_text(
            "👋 Welcome to *GigiP2Bot* — your Web3 assistant 🤖💸\n\n"
            "Say things like:\n"
            "• *Buy BTC fast*\n"
            "• *Sell TON now*\n"
            "• *Buy TON with fiat*\n"
            "• *Connect my wallet*\n\n"
            "👇 Start by picking an action:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logging.error(f"🔥 Error in /start: {e}")
        await update.message.reply_text("❌ Something went wrong while starting. Please try again.")

# ================= CALLBACK HANDLER =================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.message.chat_id

    if query.data == "select_fiat":
        keyboard = [[InlineKeyboardButton(fiat, callback_data=f"fiat_{fiat}")] for fiat in SUPPORTED_FIATS]
        await query.message.reply_text("💵 Please choose your local currency:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if query.data.startswith("fiat_"):
        fiat = query.data.replace("fiat_", "")
        user_data[uid] = {"fiat": fiat}
        user_pending_fiat[uid] = True
        await query.message.reply_text(f"💰 Great! Now enter the amount in {fiat} you want to convert to TON (e.g. 5000):")
        return

    if query.data == "buy_crypto":
        await query.message.reply_text("💵 To buy TON, please select your fiat currency using /start and follow the steps.")
        return

    if query.data == "sell_crypto":
        await query.message.reply_text("💸 Sell flow coming soon! Stay tuned.")
        return

    if query.data == "help":
        await query.message.reply_text("🛠 Need help? Try asking:\n• 'Price of BTC'\n• 'Buy USDT'\n• 'Connect wallet'\nUse /start to begin again.", parse_mode=ParseMode.MARKDOWN)
        return

    if query.data == "sign":
        msg = f"Sign this message in your wallet: GigiWallet-{uid}-{int(time.time())}"
        user_signatures[uid] = msg
        await query.message.reply_text(f"🖊 `{msg}`", parse_mode=ParseMode.MARKDOWN)
        return

    if query.data == "view_wallet":
        wallet = user_wallets.get(uid)
        if wallet:
            await query.message.reply_text(f"📦 *Your Wallet:* `{wallet['wallet_address']}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await query.message.reply_text("❌ No wallet found. Use /start to connect.")
        return

    if query.data == "history":
        history = user_orders.get(uid, [])
        if not history:
            await query.message.reply_text("📭 You have no recent orders.")
        else:
            msg = "📜 *Your Recent Orders:*\n"
            for h in history[-5:][::-1]:
                msg += f"• {h}\n"
            await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return

# ================= MESSAGE HANDLER =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.chat_id
    text = update.message.text.strip().lower()

    if text.startswith("0x") or 32 <= len(text.strip()) <= 48:
        wallet_type = "evm" if text.startswith("0x") else "ton"
        icon = "🟣" if wallet_type == "evm" else "🔷"
        user_wallets[uid] = {"wallet_address": text, "type": wallet_type}
        await update.message.reply_text(f"{icon} *{wallet_type.upper()} wallet connected:* `{text}`", parse_mode=ParseMode.MARKDOWN)
        return

    parsed = detect_sell_command(text)
    if parsed and parsed["token"] == "TON":
        amount = parsed["amount"]
        sign_link = generate_ton_sign_link(amount)
        keyboard = [[InlineKeyboardButton("✅ Sign TON Transfer", url=sign_link)]]
        user_orders.setdefault(uid, []).append(f"Sell {amount} TON")
        return

    if uid in user_pending_fiat:
        try:
            amount_fiat = float(text)
            fiat = user_data[uid]["fiat"]
            usdt_to_fiat = get_usdt_to_fiat_rate(fiat)
            ton_usdt = get_crypto_price("ton")
            if not usdt_to_fiat or not ton_usdt:
                await update.message.reply_text("❌ Couldn't fetch live rates. Try again later.")
                return
            usdt_amount = amount_fiat / usdt_to_fiat
            ton_amount = usdt_amount / ton_usdt
            nano_amount = int(ton_amount * 1e9)
            ton_sign_url = f"{TON_CONNECT_BASE}?amount={nano_amount}&to={TON_RECEIVE_ADDRESS}"
            keyboard = [[InlineKeyboardButton("✅ Sign with TON Wallet", url=ton_sign_url)]]
            await update.message.reply_text(
                f"💸 {amount_fiat:.2f} {fiat} can buy you ~<b>{ton_amount:.4f} TON</b> today.\n\nSign the transaction to continue:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            user_orders.setdefault(uid, []).append(f"Buy {ton_amount:.4f} TON for {amount_fiat} {fiat}")
            del user_pending_fiat[uid]
        except:
            await update.message.reply_text("❌ Invalid amount. Please enter a number like 5000 or 200.")
        return

    for coin in SUPPORTED_CRYPTOS:
        if coin in text:
            price = get_crypto_price(coin)
            if price:
                await update.message.reply_text(f"💰 *{coin.upper()}* is currently *${price:,.2f}*", parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(f"❌ Couldn't get {coin.upper()} price")
            user_orders.setdefault(uid, []).append(f"Checked {coin.upper()} rate")
            return

    await update.message.reply_text("🤖 You can say 'buy BTC', 'sell 5 TON', paste your wallet address, or use /start.", parse_mode=ParseMode.MARKDOWN)

# ================= RUN BOT =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("🚀 GigiP2Bot fully loaded!")
    app.run_polling()

if __name__ == "__main__":
    main()
