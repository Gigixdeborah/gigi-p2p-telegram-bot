# Gigi Webhook

## Version 1.0.0 — Production Release

Production-ready Telegram bot and webhook stack for TON, EVM, and Solana.

- **webhook_server.py** → main server script
- **requirements.txt** → dependencies
- **.env** → environment secrets
- **sign.html**, **evm.html**, **solana.html** → simple wallet signing UIs

## Setup

Install the Python requirements and the spaCy model used by the bot:

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```
cp .env.example .env
```

Key variables:

- `TELEGRAM_BOT_TOKEN` – bot token from BotFather
- `DATABASE_URL` – SQLAlchemy connection URL
- `REDIS_URL` – Redis connection (optional)
- `WEBHOOK_SECRET` – shared secret for wallet callbacks
- `ADMIN_CHAT_ID` – Telegram user ID for error notifications
- `ADMIN_TOKEN` – token required for `/generate-signature`

### Systemd Services

`gigibot.service` and `gigiwebhook.service` can be installed to run the bot and webhook on boot:

```bash
sudo cp gigibot.service /etc/systemd/system/
sudo cp gigiwebhook.service /etc/systemd/system/
sudo systemctl enable gigibot.service gigiwebhook.service
sudo systemctl start gigibot.service gigiwebhook.service
```

### Auto update

`pull_and_restart.sh` pulls the latest code and restarts the services. Add a cron job to run it every 5 minutes:

```cron
*/5 * * * * /opt/gigi-p2p-telegram-bot/pull_and_restart.sh >> /var/log/gigi_update.log 2>&1
```

### Docker
Build and run the webhook using Docker:

```bash
docker build -t gigi-webhook .
docker run -p 5000:5000 --env-file .env gigi-webhook
```

The image is tagged as `gigi-webhook:v1.0.0` for production deployments.

## Bot Setup

Run the Telegram bot with:

```bash
python bot_main.py
```

Ensure the `.env` file contains the bot token and database connection string.

## Webhook Flow

1. The HTML signing page posts the signed transaction to `/ton-webhook`, `/evm-webhook`, or `/solana-webhook`.
2. The Flask server verifies the HMAC signature and saves the record.
3. The bot notifies the user of payout status.

## Config Example

```
TELEGRAM_BOT_TOKEN=abc123
DATABASE_URL=sqlite:///gigi.db
WEBHOOK_SECRET=secret
ADMIN_CHAT_ID=12345
ADMIN_TOKEN=myadmin
```

### API Endpoints

- `POST /summarize` – JSON `{ "text": "..." }` → `{ "summary": "..." }`
- `POST /ton-webhook` – transaction log for TON
- `POST /evm-webhook` – transaction log for EVM chains
- `POST /solana-webhook` – transaction log for Solana

