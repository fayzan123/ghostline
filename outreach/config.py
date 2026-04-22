"""
outreach_config.py — Configuration constants and environment variable loading
for the Ghostline outreach agent.

Follows the same env-var loading pattern as shared/config.py.

ANTHROPIC_API_KEY is validated at import time. Missing values raise
RuntimeError immediately so errors surface before any work begins.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Environment variables — credentials
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# Sender identity (used in email drafts for display purposes)
SENDER_NAME: str = os.getenv("SENDER_NAME", "Fayzan, Co-founder of Chox")

# ---------------------------------------------------------------------------
# Fail loudly at import time if critical credentials are missing
# ---------------------------------------------------------------------------

if not ANTHROPIC_API_KEY:
    raise RuntimeError(
        "Missing required environment variable: ANTHROPIC_API_KEY. "
        "Add it to your .env file before running the outreach agent."
    )

# ---------------------------------------------------------------------------
# Batch size
# ---------------------------------------------------------------------------

BATCH_SIZE: int = 10

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

CHECKPOINT_DB: str = "data/ghostline_outreach.db"
