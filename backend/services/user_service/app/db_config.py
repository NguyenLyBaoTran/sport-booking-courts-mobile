"""Resolve the User Service DB URL without overriding explicit environment."""

import os
from pathlib import Path

from dotenv import load_dotenv


def user_database_url() -> str | None:
    # Explicit container/CI environment always wins. Dotenv remains available
    # for local development when the process has no URL configured.
    configured = os.getenv("USER_DATABASE_URL")
    if configured:
        return configured
    load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
    return os.getenv("USER_DATABASE_URL")
