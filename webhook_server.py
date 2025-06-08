from flask import Flask, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, Transaction, TransactionStatus
from utils import validate_address
import os
import logging
import requests
from functools import wraps
import hmac
import hashlib
import json

app = Flask(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_size=10)
Session = sessionmaker(bind=engine)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PAYSTACK_API_KEY = os.getenv("PAYSTACK_API_KEY")

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
        session.commit()
        logger.info(f"✅ {wallet_type} wallet saved: {wallet_address}")

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

    with Session() as session:
        try:
            if session.query(Transaction).filter_by(tx_hash=data['txHash']).first():
                return jsonify({"message": "Already exists"}), 200

            tx = Transaction(
                user_id=str(data['user_id']),
                tx_hash=data['txHash'],
                amount=float(data['amount']),
                token=data['token'].upper(),
                chain="TON",
                status=TransactionStatus.SIGNED
            )
            session.add(tx)
            session.commit()

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
            return jsonify({"error": "Server error"}), 500

@app.route('/<chain>-webhook', methods=['POST'])
@verify_webhook
def transaction_webhook(chain):
    data = request.json
    required = ['user_id', 'txHash', 'amount', 'token', 'to']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing data"}), 400

    with Session() as session:
        if session.query(Transaction).filter_by(tx_hash=data['txHash']).first():
            return jsonify({"message": "Already exists"}), 200

        tx = Transaction(
            user_id=str(data['user_id']),
            tx_hash=data['txHash'],
            amount=float(data['amount']),
            token=data['token'].upper(),
            chain=chain.upper(),
            status=TransactionStatus.SIGNED
        )
        session.add(tx)
        session.commit()

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

@app.route('/generate-signature', methods=['POST'])
def generate_signature():
    data = request.json
    payload = json.dumps(data, separators=(',', ':'))
    signature = hmac.new(WEBHOOK_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
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
