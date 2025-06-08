from flask import Flask, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, Transaction, TransactionStatus
from utils import validate_address, load_json, save_json
import os
import logging
import requests
import httpx
from functools import wraps
import hmac
import hashlib
import json

from config import (
    DATABASE_URL,
    WEBHOOK_SECRET,
    TELEGRAM_BOT_TOKEN,
)

app = Flask(__name__)
engine = create_engine(DATABASE_URL, pool_size=10)
Session = sessionmaker(bind=engine)
PAYSTACK_API_KEY = os.getenv("PAYSTACK_API_KEY")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_webhook(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        signature = request.headers.get("X-Webhook-Signature")
        if not signature or not hmac.compare_digest(
            hmac.new(WEBHOOK_SECRET.encode(), request.data, hashlib.sha256).hexdigest(),
            signature
        ):
            logger.error("❌ Invalid webhook signature")
            return jsonify({"error": "Invalid signature"}), 403
        return f(*args, **kwargs)
    return decorated_function


@app.route('/summarize', methods=['POST'])
async def summarize():
    data = request.json or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                OLLAMA_URL,
                json={
                    'model': 'llama3',
                    'messages': [{'role': 'user', 'content': text}]
                },
                timeout=20,
            )
            msg = resp.json().get('message', {}).get('content')
            return jsonify({'summary': msg or ''}), 200
    except Exception as e:
        logger.error(f"Summarize error: {e}")
        return jsonify({'error': 'Ollama error'}), 500

@app.route('/connect-webhook', methods=['POST'])
@verify_webhook
def connect_webhook():
    data = request.json
    required = ['user_id', 'wallet_type', 'wallet_address']
    if not all(k in data for k in required):
        logger.error(f"❌ Invalid data: {data}")
        return jsonify({"error": "Missing or invalid data"}), 400

    user_id = str(data['user_id'])
    wallet_type = data['wallet_type'].upper()
    wallet_address = data['wallet_address']

    if not validate_address(wallet_address, wallet_type):
        return jsonify({"error": "Invalid wallet address"}), 400

    with Session() as session:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        setattr(user, f"{wallet_type.lower()}_wallet", wallet_address)
        try:
            session.commit()
            logger.info(f"✅ {wallet_type} wallet saved: {wallet_address}")

            users = load_json("data/users.json", {})
            u = users.get(user_id, {
                "fiat_currency": user.fiat_currency,
                "lang": user.lang,
                "tone": user.tone,
                "wallets": {},
            })
            u.setdefault("wallets", {})[f"{wallet_type.lower()}_wallet"] = wallet_address
            users[user_id] = u
            save_json("data/users.json", users)
        except Exception as e:
            logger.error(f"User wallet DB error: {e}")
            session.rollback()

            users = load_json("data/users.json", {})
            u = users.setdefault(user_id, {"fiat_currency": "NGN", "lang": "EN", "tone": "playful", "wallets": {}})
            u.setdefault("wallets", {})[f"{wallet_type.lower()}_wallet"] = wallet_address
            save_json("data/users.json", users)

        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": user_id,
                "text": f"🔐 {wallet_type} Wallet Connected!\n👛 {wallet_address[:6]}...{wallet_address[-6:]}"
            },
            timeout=5
        )
        return jsonify({"message": "Wallet connected"}), 200

@app.route('/ton-webhook', methods=['POST'])
@verify_webhook
def ton_webhook():
    data = request.json
    required = ['user_id', 'txHash', 'amount', 'token', 'to']
    if not all(k in data for k in required):
        logger.error("❌ Missing TON webhook data")
        return jsonify({"error": "Invalid data"}), 400
    try:
        amount = float(data['amount'])
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount"}), 400
    token = data['token'].upper()
    if not token.isalpha():
        return jsonify({"error": "Invalid token"}), 400

    record = {
        "user_id": str(data['user_id']),
        "tx_hash": data['txHash'],
        "amount": amount,
        "token": token,
        "chain": "TON",
        "status": TransactionStatus.SIGNED.value,
    }

    with Session() as session:
        try:
            if session.query(Transaction).filter_by(tx_hash=data['txHash']).first():
                return jsonify({"message": "Already exists"}), 200

            tx = Transaction(
                user_id=record['user_id'],
                tx_hash=record['tx_hash'],
                amount=record['amount'],
                token=record['token'],
                chain=record['chain'],
                status=TransactionStatus.SIGNED
            )
            session.add(tx)
            session.commit()

            try:
                order = place_market_sell(f"{token}USDT", amount)
                logger.info(f"Bybit sell result: {order}")
                tx.bybit_order_id = order.get("result", {}).get("orderId")
                tx.fiat_amount = float(order.get("result", {}).get("cumExecValue", 0))
                tx.status = TransactionStatus.PAID
                session.commit()
                requests.post(
                    "https://api.paystack.co/transfer",
                    headers={
                        "Authorization": f"Bearer {PAYSTACK_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "source": "balance",
                        "amount": int(tx.fiat_amount * 100),
                        "recipient": {"type": "nuban"},
                        "reason": "Payout from GigiP2Bot",
                    },
                    timeout=10,
                )
            except Exception as e:
                logger.error(f"Bybit sell failed: {e}")
                tx.status = TransactionStatus.SELL_FAILED
                session.commit()
                return jsonify({"error": "Sell failed"}), 500

            txs = load_json("data/transactions.json", [])
            txs.append(record)
            save_json("data/transactions.json", txs)

            logger.info(f"✅ TON Tx signed: {data['txHash']} for {data['user_id']}")
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": data['user_id'],
                    "text": f"🎉 {data['token']} Tx Signed!\nProcessing payout..."
                },
                timeout=5
            )
            return jsonify({"message": "TON transaction recorded"}), 200
        except Exception as e:
            logger.error(f"❌ TON webhook error: {e}")
            session.rollback()

    txs = load_json("data/transactions.json", [])
    if not any(t.get("tx_hash") == record['tx_hash'] for t in txs):
        txs.append(record)
        save_json("data/transactions.json", txs)
    return jsonify({"message": "TON transaction recorded"}), 200

@app.route('/<chain>-webhook', methods=['POST'])
@verify_webhook
def transaction_webhook(chain):
    data = request.json
    required = ['user_id', 'txHash', 'amount', 'token', 'to']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing data"}), 400
    try:
        amount = float(data['amount'])
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount"}), 400
    token = data['token'].upper()
    if not token.isalpha():
        return jsonify({"error": "Invalid token"}), 400

    record = {
        "user_id": str(data['user_id']),
        "tx_hash": data['txHash'],
        "amount": amount,
        "token": token,
        "chain": chain.upper(),
        "status": TransactionStatus.SIGNED.value,
    }

    with Session() as session:
        try:
            if session.query(Transaction).filter_by(tx_hash=data['txHash']).first():
                return jsonify({"message": "Already exists"}), 200

            tx = Transaction(
                user_id=record['user_id'],
                tx_hash=record['tx_hash'],
                amount=record['amount'],
                token=record['token'],
                chain=record['chain'],
                status=TransactionStatus.SIGNED
            )
            session.add(tx)
            session.commit()

            try:
                order = place_market_sell(f"{token}USDT", amount)
                logger.info(f"Bybit sell result: {order}")
                tx.bybit_order_id = order.get("result", {}).get("orderId")
                tx.fiat_amount = float(order.get("result", {}).get("cumExecValue", 0))
                tx.status = TransactionStatus.PAID
                session.commit()
                requests.post(
                    "https://api.paystack.co/transfer",
                    headers={
                        "Authorization": f"Bearer {PAYSTACK_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "source": "balance",
                        "amount": int(tx.fiat_amount * 100),
                        "recipient": {"type": "nuban"},
                        "reason": "Payout from GigiP2Bot",
                    },
                    timeout=10,
                )
            except Exception as e:
                logger.error(f"Bybit sell failed: {e}")
                tx.status = TransactionStatus.SELL_FAILED
                session.commit()
                return jsonify({"error": "Sell failed"}), 500

            txs = load_json("data/transactions.json", [])
            txs.append(record)
            save_json("data/transactions.json", txs)

            logger.info(f"✅ {chain} TX logged: {data['txHash']}")
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": data['user_id'],
                    "text": f"🎉 {data['token']} Tx Signed!\nProcessing payout..."
                },
                timeout=5
            )
            return jsonify({"message": "Transaction recorded"}), 200
        except Exception as e:
            logger.error(f"❌ {chain} webhook error: {e}")
            session.rollback()

    txs = load_json("data/transactions.json", [])
    if not any(t.get("tx_hash") == record['tx_hash'] for t in txs):
        txs.append(record)
        save_json("data/transactions.json", txs)
    return jsonify({"message": "Transaction recorded"}), 200

@app.route('/generate-signature', methods=['POST'])
def generate_signature():
    admin_token = os.getenv("ADMIN_TOKEN")
    if not admin_token or request.headers.get("X-Admin-Token") != admin_token:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    payload = json.dumps(data, separators=(',', ':'))
    signature = hmac.new(
        WEBHOOK_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return jsonify({"signature": signature})

@app.route('/paystack-callback', methods=['POST'])
def paystack_callback():
    return jsonify({"message": "✅ Callback received"}), 200

@app.route('/paystack-webhook', methods=['POST'])
def paystack_webhook():
    data = request.json
    logger.info(f"💰 Paystack Webhook Triggered: {data}")

    if data.get("event") == "charge.success":
        metadata = data["data"].get("metadata", {})
        user_id = metadata.get("user_id")
        amount = data["data"].get("amount", 0) / 100
        bank_account = metadata.get("bank_account")
        bank_code = metadata.get("bank_code")
        currency = data["data"].get("currency", "NGN")

        if not all([user_id, amount, bank_account, bank_code]):
            logger.error("❌ Incomplete payout data")
            return jsonify({"error": "Incomplete payout data"}), 400

        headers = {
            "Authorization": f"Bearer {PAYSTACK_API_KEY}",
            "Content-Type": "application/json"
        }
        payout_data = {
            "source": "balance",
            "amount": int(amount * 100),
            "recipient": {
                "type": "nuban",
                "name": "Gigi User",
                "account_number": bank_account,
                "bank_code": bank_code,
                "currency": currency
            },
            "reason": "Payout from GigiP2Bot"
        }

        try:
            payout_response = requests.post("https://api.paystack.co/transfer", headers=headers, json=payout_data)
            if payout_response.status_code == 200:
                logger.info(f"✅ Payout success: {payout_response.json()}")
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": user_id,
                        "text": f"💸 Your {currency} payout has been processed!"
                    }
                )
                return jsonify({"message": "Payout successful"}), 200
            else:
                logger.error(f"❌ Paystack payout failed: {payout_response.text}")
                return jsonify({"error": "Payout failed"}), 500
        except Exception as e:
            logger.error(f"❌ Exception during payout: {e}")
            return jsonify({"error": "Payout error"}), 500

    return jsonify({"message": "Webhook event ignored"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
