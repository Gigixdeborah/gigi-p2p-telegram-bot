import os
import logging
from typing import Dict
from pybit.unified_trading import HTTP

logger = logging.getLogger(__name__)

API_KEY = os.getenv("BYBIT_API_KEY")
API_SECRET = os.getenv("BYBIT_API_SECRET")

session = HTTP(api_key=API_KEY, api_secret=API_SECRET)


def place_market_sell(token_symbol: str, amount: float) -> Dict:
    """Place a market sell order on Bybit."""
    try:
        return session.place_order(
            category="spot",
            symbol=token_symbol,
            side="Sell",
            orderType="Market",
            qty=amount,
        )
    except Exception as e:
        logger.error(f"Bybit sell error: {e}")
        raise


def get_balance(asset: str) -> float:
    """Get asset balance from Bybit wallet."""
    try:
        res = session.get_wallet_balance(accountType="SPOT", coin=asset)
        coin_data = res["result"]["list"][0]["coin"][0]
        return float(coin_data["walletBalance"])
    except Exception as e:
        logger.error(f"Bybit balance error: {e}")
        raise
