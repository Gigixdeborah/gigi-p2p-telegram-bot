# Gigi P2P Telegram Bot

Production refactor with:
- Telegram bot (`bot.py`)
- FastAPI webhook service (`webhook.py`)
- Render deployment (`render.yaml`)
- Alembic migrations (`alembic/`)

## Runtime services

- Bot worker: `python bot.py`
- Webhook API: `uvicorn webhook:app --host 0.0.0.0 --port 8000`
- Health check: `GET /health -> {"status":"ok"}`

## Webhook endpoints

- `/nomba-webhook`
- `/transak-webhook`
- `/ton-webhook`
- `/evm-webhook`
- `/solana-webhook`

All webhook routes verify signatures using `WEBHOOK_SECRET` and store idempotency records in `webhook_events`.

## Commands

Core:
- `/start`, `/kyc`, `/buy`, `/sell`, `/order <id>`, `/orders`, `/cancel <id>`, `/wallet`, `/balance`, `/history`

Support:
- `/help`, `/status`, `/price <token>`, `/rates`, `/fees`, `/support`

Admin (admin user only):
- `/admin orders`
- `/admin users`
- `/admin retry <order_id>`
- `/admin cancel <order_id>`
- `/admin logs`
- `/admin stats`

## Migrations

```bash
alembic upgrade head
```

## Render

`render.yaml` provisions:
- `gigi-webhook` (web)
- `gigi-bot` (worker)
- `gigi-postgres` (managed postgres)
- with `preDeployCommand: alembic upgrade head`
