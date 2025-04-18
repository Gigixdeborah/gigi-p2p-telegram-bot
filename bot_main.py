import os
import openai
import re
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI API key
openai.api_key = OPENAI_API_KEY

def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("💰 Buy Crypto", callback_data="buy")],
        [InlineKeyboardButton("📉 Sell Crypto", callback_data="sell")],
        [InlineKeyboardButton("🔗 Connect Wallet", callback_data="connect_wallet")],
        [InlineKeyboardButton("📊 Exchange Rates", callback_data="rates")],
        [InlineKeyboardButton("💵 Fiat Rates", callback_data="fiatrates")],
        [InlineKeyboardButton("💳 Make a Payment", callback_data="payment")],
        [InlineKeyboardButton("💼 Check Balance", callback_data="balance")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔹 Welcome to GigiP2Bot! 🔹\n\nHow can I assist you today?", reply_markup=main_keyboard())

async def chatgpt_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.lower()
    
    # Check if user wants to buy/sell crypto
    buy_match = re.search(r"buy (\d+) (\w+)", user_message)
    sell_match = re.search(r"sell (\d+) (\w+)", user_message)
    
    if buy_match:
        amount, currency = buy_match.groups()
        await update.message.reply_text(f"✅ Processing your order to buy {amount} {currency.upper()}...")
        return
    
    if sell_match:
        amount, currency = sell_match.groups()
        await update.message.reply_text(f"✅ Processing your order to sell {amount} {currency.upper()}...")
        return
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": user_message}]
        )
        ai_text = response["choices"][0]["message"]["content"]
        await update.message.reply_text(ai_text)
    except Exception as e:
        await update.message.reply_text("❌ An error occurred while processing your request.")
        print(f"OpenAI API Error: {e}")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    actions = {
        "buy": "You chose to Buy Crypto! Please specify the amount and currency.",
        "sell": "You chose to Sell Crypto! Please specify the amount and currency.",
        "connect_wallet": "🔗 Connecting wallet... Follow the instructions.",
        "rates": "📊 Checking exchange rates... Fetching live data.",
        "fiatrates": "💵 Getting fiat conversion rates... Please wait.",
        "payment": "💳 Processing payment... Enter details.",
        "balance": "💼 Checking balance... Fetching your data."
    }
    
    await query.edit_message_text(text=actions.get(query.data, "Unknown action!"))

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chatgpt_response))
    app.add_handler(CallbackQueryHandler(button_click))
    
    print("✅ Bot is running with Supercharged ChatGPT...")
    app.run_polling()

if __name__ == "__main__":
    main()
