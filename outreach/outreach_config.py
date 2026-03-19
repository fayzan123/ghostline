"""
outreach_config.py — Configuration constants and environment variable loading
for the Ghostline outreach agent.

Follows the same env-var loading pattern as shared/config.py.

Critical credentials (SMTP_USERNAME, SMTP_PASSWORD, ANTHROPIC_API_KEY) are
validated at import time. Missing values raise RuntimeError immediately so
errors surface before any work begins.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Environment variables — credentials
# ---------------------------------------------------------------------------

SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# Sender identity
SENDER_NAME: str = os.getenv("SENDER_NAME", "Fayzan and Dilraj, Co-founders of Chox")
SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", SMTP_USERNAME)

# ---------------------------------------------------------------------------
# Fail loudly at import time if critical credentials are missing
# ---------------------------------------------------------------------------

_missing: list[str] = []

if not SMTP_USERNAME:
    _missing.append("SMTP_USERNAME")
if not SMTP_PASSWORD:
    _missing.append("SMTP_PASSWORD")
if not ANTHROPIC_API_KEY:
    _missing.append("ANTHROPIC_API_KEY")

if _missing:
    raise RuntimeError(
        f"Missing required environment variable(s): {', '.join(_missing)}. "
        "Add them to your .env file before running the outreach agent."
    )

# ---------------------------------------------------------------------------
# SMTP constants
# ---------------------------------------------------------------------------

SMTP_HOST: str = "smtp.gmail.com"
SMTP_PORT: int = 587  # STARTTLS
# To switch to Microsoft 365 later: SMTP_HOST = "smtp.office365.com" (port stays 587)

# ---------------------------------------------------------------------------
# Send pacing
# ---------------------------------------------------------------------------

BATCH_SIZE: int = 10
MIN_SEND_DELAY_SECONDS: int = 90
MAX_SEND_DELAY_SECONDS: int = 180
MAX_EMAILS_PER_DAY: int = 20          # Adjust upward as warm-up progresses
MAX_EMAILS_PER_30_MIN: int = 5

# ---------------------------------------------------------------------------
# Claude API
# ---------------------------------------------------------------------------

CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS: int = 1024
CLAUDE_TEMPERATURE: float = 0.7       # Some creativity for personalization

# ---------------------------------------------------------------------------
# README fetch
# ---------------------------------------------------------------------------

README_MAX_CHARS: int = 2000          # Truncate READMEs to this length

# ---------------------------------------------------------------------------
# LangGraph checkpoint
# ---------------------------------------------------------------------------

CHECKPOINT_DB: str = "ghostline_outreach.db"
