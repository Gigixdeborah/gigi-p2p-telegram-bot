import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
TWA_BASE_URL = os.getenv(
    "TWA_BASE_URL", "https://gigi-wallet-signing.onrender.com"
)
BYBIT_API_URL = "https://api.bybit.com"
BYBIT_RECIPIENT_API_URL = os.getenv(
    "BYBIT_RECIPIENT_API_URL", "https://api.bybit.com/custom/recipient"
)
TRANSACTIONS_FILE = os.getenv("TRANSACTIONS_FILE", "data/transactions.json")

REQUIRED_ENV_VARS = [
    "TELEGRAM_BOT_TOKEN",
    "DATABASE_URL",
    "ADMIN_CHAT_ID",
    "WEBHOOK_SECRET",
]
for var in REQUIRED_ENV_VARS:
    if not globals().get(var):
        raise EnvironmentError(f"Missing required environment variable: {var}")
