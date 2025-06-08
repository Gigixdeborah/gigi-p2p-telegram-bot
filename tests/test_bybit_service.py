import sys
from pathlib import Path
from unittest.mock import MagicMock
sys.path.append(str(Path(__file__).resolve().parents[1]))

import bybit_service


def test_place_market_sell():
    bybit_service.session = MagicMock()
    bybit_service.session.place_order.return_value = {"retCode": 0, "result": {"orderId": "123", "cumExecValue": "10"}}
    res = bybit_service.place_market_sell("BTCUSDT", 1)
    bybit_service.session.place_order.assert_called_with(category="spot", symbol="BTCUSDT", side="Sell", orderType="Market", qty=1)
    assert res["retCode"] == 0


def test_get_balance():
    bybit_service.session = MagicMock()
    bybit_service.session.get_wallet_balance.return_value = {"result": {"list": [{"coin": [{"walletBalance": "5"}]}]}}
    bal = bybit_service.get_balance("BTC")
    bybit_service.session.get_wallet_balance.assert_called_with(accountType="SPOT", coin="BTC")
    assert bal == 5.0
