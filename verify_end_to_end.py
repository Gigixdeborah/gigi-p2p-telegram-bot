import os
import json
import time
import hmac
import hashlib
import requests
import psycopg2

API_URL = os.getenv('API_URL', 'http://localhost:5000')
BOT_TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN', 'TEST_TOKEN')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'secret')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/postgres')
TEST_CHAT_ID = int(os.getenv('TEST_CHAT_ID', '0'))


def print_step(title):
    print(f"\n=== {title} ===")


def get_updates():
    try:
        resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", timeout=10)
        return resp.json().get('result', [])
    except Exception as e:
        print(f"[WARN] Failed to fetch Telegram updates: {e}")
        return []


def has_new_bot_message(before, after, chat_id):
    before_ids = {u['update_id'] for u in before}
    for u in after:
        if u.get('update_id') not in before_ids:
            msg = u.get('message') or u.get('edited_message')
            if msg and msg.get('from', {}).get('is_bot') and msg.get('chat', {}).get('id') == chat_id:
                return msg.get('text', '')
    return None


def test_summarize(text):
    print_step('Test /summarize endpoint')
    try:
        r = requests.post(f"{API_URL}/summarize", json={'text': text}, timeout=20)
        if r.status_code == 200:
            data = r.json()
            summary = data.get('summary')
            if summary:
                print('[PASS] /summarize returned:', summary)
                return summary
        print('[FAIL] /summarize response:', r.text)
    except Exception as e:
        print('[FAIL] /summarize request failed:', e)
    return None


def test_webhook(payload):
    print_step('Test /ton-webhook transaction logging')
    raw = json.dumps(payload)
    sig = hmac.new(WEBHOOK_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()
    headers = {'X-Webhook-Signature': sig}

    before = get_updates()
    try:
        r = requests.post(f"{API_URL}/ton-webhook", json=payload, headers=headers, timeout=20)
        if r.status_code == 200:
            print('[PASS] Webhook accepted')
        else:
            print('[FAIL] Webhook status:', r.status_code, r.text)
    except Exception as e:
        print('[FAIL] Error calling webhook:', e)
        return

    # Verify DB record
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT tx_hash FROM transactions WHERE tx_hash=%s", (payload['txHash'],))
        found = cur.fetchone() is not None
        cur.close(); conn.close()
        print('[PASS] Transaction stored in DB' if found else '[FAIL] Transaction not found in DB')
    except Exception as e:
        print('[FAIL] Database check error:', e)

    time.sleep(3)
    after = get_updates()
    msg = has_new_bot_message(before, after, payload['user_id'])
    if msg:
        print('[PASS] Telegram notification sent:', msg)
    else:
        print('[FAIL] Telegram notification not detected')


def test_bot_summarize(text, expected):
    print_step('Test bot /summarize command')
    before = get_updates()
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={'chat_id': TEST_CHAT_ID, 'text': f'/summarize {text}'},
            timeout=10
        )
    except Exception as e:
        print('[FAIL] Could not send command to bot:', e)
        return

    time.sleep(5)
    after = get_updates()
    reply = has_new_bot_message(before, after, TEST_CHAT_ID)
    if reply is None:
        print('[FAIL] No bot reply received')
    elif reply.strip() == expected.strip():
        print('[PASS] Bot summarized correctly')
    else:
        print('[FAIL] Bot summary mismatch')
        print(' Expected:', expected)
        print(' Received:', reply)


def main():
    sample_text = (
        "This is a sample paragraph intended to test the summarization "
        "capabilities of the Gigi application."
    )

    summary = test_summarize(sample_text)
    if summary:
        webhook_payload = {
            'user_id': TEST_CHAT_ID,
            'txHash': '0xtesthash12345',
            'amount': 5.0,
            'token': 'TON',
            'to': 'FakeWalletAddress'
        }
        test_webhook(webhook_payload)
        test_bot_summarize(sample_text, summary)


if __name__ == '__main__':
    main()
