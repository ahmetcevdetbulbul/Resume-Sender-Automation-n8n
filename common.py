"""Shared helpers for the cyberpark-outreach pipeline."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

PLACEHOLDER_EMAIL_DOMAINS = {
    "sentry.io",
    "wixpress.com",
    "example.com",
    "domain.com",
    "yourdomain.com",
    "email.com",
    "test.com",
    "godaddy.com",
    "cloudflare.com",
}


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def is_placeholder_email(email: str) -> bool:
    email = email.lower()
    domain = email.split("@")[-1]
    return domain in PLACEHOLDER_EMAIL_DOMAINS or domain.endswith(".png") or domain.endswith(".jpg")
