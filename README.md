# Gigi P2P Telegram Bot

This repository contains the Telegram bot that powers the Gigi P2P platform along with the static wallet signing pages. The webhook API is now hosted in a separate service.

- **bot.py** – main bot script
- **requirements.txt** – Python dependencies
- **sign.html**, **evm.html**, **solana.html** – wallet signing UIs used in Telegram Web Apps

## Setup

Install the Python requirements and the spaCy model used by the bot:

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

Key variables:

- `TELEGRAM_BOT_TOKEN` – bot token from BotFather
- `DATABASE_URL` – SQLAlchemy connection URL
- `REDIS_URL` – Redis connection (optional)
- `WEBHOOK_SECRET` – shared secret for wallet callbacks
- `WEBHOOK_BASE` – URL of the webhook API server
- `ADMIN_CHAT_ID` – Telegram user ID for error notifications
- `OLLAMA_HOST` – Ollama server base URL (default `http://localhost:11434`)
- `OLLAMA_MODEL` – LLM model name (default `llama3`)

### Bot Commands

- `/start` – get started and connect your wallet
- `/set_tone` – change the bot's reply style
- `/set_language` – select English, French, Spanish or Chinese
- `/balance` – check your on-chain balance
- `/transactions` – view recent transactions
- `/summarize` – summarize provided text using the LLM

### Systemd Service

`gigibot.service` can be installed to run the bot on boot:

```bash
sudo cp gigibot.service /etc/systemd/system/
sudo systemctl enable gigibot.service
sudo systemctl start gigibot.service
```

### Auto update

`pull_and_restart.sh` pulls the latest code and restarts the service. Add a cron job to run it every 5 minutes:

```cron
*/5 * * * * /opt/gigi-p2p-telegram-bot/pull_and_restart.sh >> /var/log/gigi_update.log 2>&1
```

### Docker

Build and run the bot using Docker:

```bash
docker build -t gigi-bot .
docker run --env-file .env gigi-bot
```

