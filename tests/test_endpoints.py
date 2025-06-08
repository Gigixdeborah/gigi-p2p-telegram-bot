import os
import json
import importlib
from pathlib import Path
import sys
from unittest import mock
import hmac
import hashlib
import pytest

try:
    import flask  # noqa
except ImportError:  # pragma: no cover - skip if flask missing
    pytest.skip("Flask not installed", allow_module_level=True)

sys.path.append(str(Path(__file__).resolve().parents[1]))

# set environment variables before importing webhook_server
os.environ.setdefault('TELEGRAM_BOT_TOKEN', 't')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('ADMIN_CHAT_ID', '1')
os.environ.setdefault('WEBHOOK_SECRET', 'secret')
os.environ.setdefault('ADMIN_TOKEN', 'admintest')

webhook_server = importlib.import_module('webhook_server')
from models import Base

# create tables on the in-memory database
Base.metadata.create_all(bind=webhook_server.engine)


def client():
    webhook_server.app.config['TESTING'] = True
    return webhook_server.app.test_client()


def test_generate_signature():
    c = client()
    res = c.post('/generate-signature', json={'x': 1}, headers={'X-Admin-Token': 'admintest'})
    assert res.status_code == 200
    assert 'signature' in res.get_json()


def test_ton_webhook_invalid(monkeypatch):
    c = client()
    res = c.post('/ton-webhook', json={})
    assert res.status_code == 403 or res.status_code == 400


def test_ton_webhook_valid(monkeypatch):
    with mock.patch('requests.post') as rp:
        rp.return_value.status_code = 200
        payload = {
            'user_id': '1',
            'txHash': 'abc',
            'amount': 1.0,
            'token': 'USDT',
            'to': 'addr'
        }
        body = json.dumps(payload)
        sig = hmac.new(b'secret', body.encode(), hashlib.sha256).hexdigest()
        c = client()
        res = c.post('/ton-webhook', data=body, headers={'Content-Type': 'application/json', 'X-Webhook-Signature': sig})
        assert res.status_code == 200

