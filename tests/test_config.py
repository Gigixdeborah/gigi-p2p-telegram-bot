import importlib
import os
import pytest

try:
    import dotenv  # noqa
except ImportError:
    pytest.skip("dotenv not installed", allow_module_level=True)

required = {
    'TELEGRAM_BOT_TOKEN': 't',
    'DATABASE_URL': 'sqlite:///:memory:',
    'ADMIN_CHAT_ID': '1',
    'WEBHOOK_SECRET': 'secret'
}


def setup_env(monkeypatch):
    for k, v in required.items():
        monkeypatch.setenv(k, v)


def test_valid_config(monkeypatch):
    setup_env(monkeypatch)
    cfg = importlib.import_module('config')
    importlib.reload(cfg)
    assert cfg.TELEGRAM_BOT_TOKEN == 't'


def test_missing_env(monkeypatch):
    setup_env(monkeypatch)
    monkeypatch.delenv('TELEGRAM_BOT_TOKEN', raising=False)
    with pytest.raises(EnvironmentError):
        importlib.reload(importlib.import_module('config'))
