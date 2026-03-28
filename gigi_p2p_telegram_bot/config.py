"""
Configuration module for the production Gigi crypto platform.

This module loads environment variables needed across the
Telegram bot, webhook server, and external service integrations.

Using a single configuration module ensures that settings are
centralised and easy to manage. Environment variables are
loaded from a `.env` file if present or from the deployment
environment (e.g. Render). Required variables should be set
at deployment time for security.
"""

import os
from dotenv import load_dotenv


# Attempt to load variables from a .env file if it exists.  This is
# optional in production where Render provides environment variables
# directly. If the file isn't present the call is a no‑op.
load_dotenv()

# Telegram bot configuration
TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID: str | None = os.getenv("ADMIN_CHAT_ID")

# Database configuration.  Render will inject DATABASE_URL for
# Postgres databases.  In local development you can point this at a
# local Postgres instance or SQLite for quick testing.
DATABASE_URL: str | None = os.getenv("DATABASE_URL")

# Base URL for serving the Telegram web app wallet signing pages.
# This should point at the Render static service hosting the
# HTML/JS pages for TON, EVM, and Solana signing flows.
TWA_BASE_URL: str = os.getenv("TWA_BASE_URL", "")

# Base URL of the webhook service.  The Telegram bot uses this to
# send summarisation requests and to notify the server of completed
# transactions.  In production this will be a Render service URL.
WEBHOOK_BASE: str | None = os.getenv("WEBHOOK_BASE")

# Secret used to sign webhook requests and verify their integrity.
WEBHOOK_SECRET: str | None = os.getenv("WEBHOOK_SECRET")

# API keys for external providers.  These must be configured in
# Render or your local environment.  Never commit real keys to
# source control.
NOMBA_API_KEY: str | None = os.getenv("NOMBA_API_KEY")
TRANSAK_API_KEY: str | None = os.getenv("TRANSAK_API_KEY")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")

# Base URLs for external providers.  These allow you to override
# endpoints in non‑production environments or point at sandboxes.  When
# omitted the provider client modules will use their default production
# hosts.  See ``nomba_api`` and ``transak_api`` for details.
NOMBA_BASE_URL: str | None = os.getenv("NOMBA_BASE_URL")
TRANSAK_BASE_URL: str | None = os.getenv("TRANSAK_BASE_URL")

__all__ = [
    "TELEGRAM_BOT_TOKEN",
    "ADMIN_CHAT_ID",
    "DATABASE_URL",
    "TWA_BASE_URL",
    "WEBHOOK_BASE",
    "WEBHOOK_SECRET",
    "NOMBA_API_KEY",
    "TRANSAK_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "NOMBA_BASE_URL",
    "TRANSAK_BASE_URL",
]
