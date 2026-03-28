import os
from dotenv import load_dotenv

load_dotenv()


def _to_async_db_url(url: str | None) -> str | None:
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ASYNC_DATABASE_URL = _to_async_db_url(DATABASE_URL)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE", "http://localhost:5000")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
TWA_BASE_URL = os.getenv("TWA_BASE_URL", "https://gigi-wallet-signing.onrender.com")
BYBIT_API_URL = "https://api.bybit.com"
BYBIT_RECIPIENT_API_URL = os.getenv("BYBIT_RECIPIENT_API_URL", "https://api.bybit.com/custom/recipient")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
TRANSACTIONS_FILE = os.getenv("TRANSACTIONS_FILE", "data/transactions.json")


def validate_required_env(service: str) -> None:
    required_by_service = {
        "bot": ["TELEGRAM_BOT_TOKEN", "DATABASE_URL", "ADMIN_CHAT_ID", "WEBHOOK_SECRET"],
        "webhook": ["DATABASE_URL", "WEBHOOK_SECRET"],
    }
    for var in required_by_service.get(service, []):
        if not os.getenv(var):
            raise EnvironmentError(f"Missing required environment variable: {var}")
