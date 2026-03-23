#!/usr/bin/env python3
"""
score_leads.py — Chox fit scorer for Ghostline leads.

Reads all leads from the Google Sheet, scores each unscored lead against
the Chox ICP using Claude Haiku, and writes fit_score + fit_reason back
to the sheet as new columns.

Usage:
    python score_leads.py             # score all unscored leads
    python score_leads.py --limit 50  # score at most 50 leads this run
"""

import argparse
import json
import logging
import os
import re
import sys
import time

import anthropic
import gspread
from dotenv import load_dotenv

from discovery.github_client import GitHubClient
from outreach.readme_fetcher import fetch_readme

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", "service_account.json")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

MODEL = "claude-haiku-4-5-20251001"

FIT_SCORE_COL = "fit_score"
FIT_REASON_COL = "fit_reason"

SHEETS_COOLDOWN = 1.5   # seconds between sheet writes
CLAUDE_COOLDOWN = 0.05  # seconds between Claude API calls
BATCH_SIZE = 10         # write back to sheet every N scored leads
README_MAX_CHARS = 3000 # README chars sent to Claude (more than outreach; scoring needs more signal)

# ---------------------------------------------------------------------------
# Chox ICP rubric
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a lead qualification specialist for Chox.

HOW CHOX WORKS:
Chox is an AI agent governance layer. Developers integrate it via an SDK using guard.wrap(),
which wraps individual tool functions before they are registered with the agent:

    charge_card = guard.wrap("stripe.create_charge", _charge_card_fn)
    run_query   = guard.wrap("postgres.execute", _run_query_fn)

The wrapped function behaves identically to the original — but every invocation is logged,
risk-scored, and evaluated by Chox before execution. Chox intercepts the tool call at the
point where the agent's decision becomes an API call.

CRITICAL IMPLEMENTATION REQUIREMENT:
Chox can ONLY be implemented if the project has real tool functions — raw callables that
the agent invokes against external services (Stripe, Postgres, Twilio, Slack, etc.).
Projects that are purely RAG pipelines, knowledge search, or LLM text generation with no
tool calls have NOTHING to wrap. They cannot implement Chox regardless of desire.

THE ONE QUESTION THAT MATTERS:
Does this project have real tool functions that an agent invokes against external services,
where Chox's governance (logging, risk scoring, blocking) would be useful?

It does NOT matter whether the project is a hobby, student work, personal tool, or enterprise product.
A solo developer calling Stripe in their side project has the same need as a company.
The ONLY criteria is: are there wrappable tool functions with real external API calls?

STRONG FIT SIGNALS (raise score):
- risk_apis_detected is non-empty (stripe, twilio, sendgrid, plaid, postgres, etc.) — hard confirmation
- README or description shows the agent autonomously calls external APIs: payments, databases, email/SMS, file systems, CRMs
- Agent uses ToolNode, AgentExecutor, or create_react_agent with real tools (not just LLM chains)
- Tool functions have side effects: they move money, write data, send messages, modify external state

POOR FIT SIGNALS (lower score):
- Pure knowledge/search/RAG pipeline — LLM reads documents and returns text, nothing to wrap
- Tutorial, demo, course, or learning project with no real integrations
- The project IS an agent governance or observability platform (direct competitor to Chox)
- Agent only reads/retrieves data and returns text — no write, financial, or communication side effects
- Framework or library for building agents (not an agent itself)

SCORING RUBRIC (1-5):
5 — Clear fit: agent has real wrappable tool calls to financial/communication/database/external APIs
4 — Strong fit: evidence of real tool calling with external services, minor ambiguity on specifics
3 — Possible fit: agentic architecture present but unclear whether tool calls touch real external services
2 — Unlikely fit: minimal evidence of real tool calls, mostly RAG or text generation
1 — No fit: pure RAG/search, no tool functions, tutorial/demo, framework/library, or direct competitor

Respond with ONLY valid JSON in this exact format, nothing else:
{"score": <1-5>, "reason": "<one concise sentence explaining the score>"}"""


def score_lead(client: anthropic.Anthropic, lead: dict, readme: str, model: str = MODEL) -> tuple[int, str]:
    """Score a single lead against the Chox ICP. Returns (score, reason)."""
    relevant = {
        "repo_name": lead.get("repo_name", ""),
        "repo_description": lead.get("repo_description", ""),
        "repo_stars": lead.get("repo_stars", ""),
        "frameworks_detected": lead.get("frameworks_detected", ""),
        "risk_apis_detected": lead.get("risk_apis_detected", ""),
        "profile_bio": lead.get("profile_bio", ""),
        "profile_company": lead.get("profile_company", ""),
        "profile_location": lead.get("profile_location", ""),
        "readme": readme if readme else "(no README available)",
    }

    response = client.messages.create(
        model=model,
        max_tokens=150,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Score this lead for Chox fit:\n\n{json.dumps(relevant, indent=2)}",
            }
        ],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences — Haiku sometimes wraps output despite instructions
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()

    try:
        result = json.loads(text)
        score = int(result["score"])
        reason = str(result["reason"])
        if not 1 <= score <= 5:
            raise ValueError(f"Score out of range: {score}")
        return score, reason
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        raise ValueError(
            f"Unparseable response for '{lead.get('github_username')}': {exc} | Raw: {text[:120]}"
        ) from exc


def col_num_to_letter(n: int) -> str:
    """Convert 1-based column number to letter (1=A, 27=AA, etc.)."""
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


def get_or_create_column(
    worksheet: gspread.Worksheet, headers: list[str], col_name: str
) -> int:
    """Return 1-based column index for col_name, adding it as a header if missing."""
    if col_name in headers:
        return headers.index(col_name) + 1

    new_col_idx = len(headers) + 1
    col_letter = col_num_to_letter(new_col_idx)
    worksheet.add_cols(1)
    time.sleep(SHEETS_COOLDOWN)
    worksheet.update([[col_name]], f"{col_letter}1")
    logger.info("Added column '%s' at column %s.", col_name, col_letter)
    headers.append(col_name)
    time.sleep(SHEETS_COOLDOWN)
    return new_col_idx


def flush_batch(
    worksheet: gspread.Worksheet, batch: list[dict], label: str = ""
) -> None:
    if not batch:
        return
    worksheet.batch_update(batch, value_input_option="RAW")
    logger.info("Wrote %d scores to sheet.%s", len(batch), f" ({label})" if label else "")
    time.sleep(SHEETS_COOLDOWN)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score Ghostline leads for Chox fit.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of leads to process this run (default: all)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=MODEL,
        help=f"Claude model to use for scoring (default: {MODEL})",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Re-score already-scored leads with --model and print comparison. Does not write to sheet.",
    )
    args = parser.parse_args()

    # Validate env
    missing = [k for k, v in [("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY), ("SPREADSHEET_ID", SPREADSHEET_ID)] if not v]
    if missing:
        logger.error("Missing required env vars: %s", ", ".join(missing))
        sys.exit(1)

    # Connect to sheet
    logger.info("Connecting to Google Sheet...")
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.sheet1
    logger.info("Connected: '%s'", spreadsheet.title)

    # Load all sheet data
    all_values = worksheet.get_all_values()
    if not all_values:
        logger.error("Sheet is empty.")
        sys.exit(1)

    headers = list(all_values[0])
    rows = all_values[1:]
    logger.info("Loaded %d leads.", len(rows))

    # Ensure fit_score and fit_reason columns exist
    fit_score_col = get_or_create_column(worksheet, headers, FIT_SCORE_COL)
    fit_reason_col = get_or_create_column(worksheet, headers, FIT_REASON_COL)

    score_col_letter = col_num_to_letter(fit_score_col)
    reason_col_letter = col_num_to_letter(fit_reason_col)
    score_col_i = fit_score_col - 1  # 0-based index into row

    # Find target rows depending on mode
    unscored = []
    for row_idx, row in enumerate(rows, start=2):
        padded = row + [""] * max(0, len(headers) - len(row))
        existing_score = padded[score_col_i].strip()
        lead_dict = dict(zip(headers, padded))
        lead_dict["_row_idx"] = row_idx
        if args.compare:
            # Compare mode: only re-score leads that already have a Haiku score
            if existing_score:
                lead_dict["_existing_score"] = existing_score
                lead_dict["_existing_reason"] = padded[fit_reason_col - 1].strip()
                unscored.append(lead_dict)
        else:
            if not existing_score:
                unscored.append(lead_dict)

    if args.compare:
        logger.info("Compare mode: %d scored leads available for re-scoring.", len(unscored))
    else:
        logger.info("Unscored leads: %d", len(unscored))

    if not unscored:
        logger.info("All leads already scored." if not args.compare else "No scored leads found to compare.")
        return

    to_score = unscored[: args.limit] if args.limit else unscored
    active_model = args.model
    logger.info(
        "%s %d leads with %s...",
        "Comparing" if args.compare else "Scoring",
        len(to_score),
        active_model,
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    github = GitHubClient()

    batch: list[dict] = []
    scored = errors = 0

    try:
        for i, lead in enumerate(to_score, start=1):
            username = lead.get("github_username") or f"row_{lead['_row_idx']}"
            row_idx = lead["_row_idx"]

            try:
                readme = fetch_readme(lead, github)
                if readme:
                    readme = readme[:README_MAX_CHARS]
                score, reason = score_lead(client, lead, readme, model=active_model)

                if args.compare:
                    old_score = lead.get("_existing_score", "?")
                    old_reason = lead.get("_existing_reason", "")
                    match = "✓ AGREE" if str(score) == str(old_score) else "✗ DIFFER"
                    print(
                        f"\n[{i}/{len(to_score)}] {username}\n"
                        f"  Haiku : {old_score}/5 — {old_reason[:100]}\n"
                        f"  {active_model.split('-')[1].capitalize()}: {score}/5 — {reason[:100]}\n"
                        f"  {match}"
                    )
                else:
                    logger.info(
                        "[%d/%d] %-30s → %d/5: %s",
                        i, len(to_score), username, score, reason[:80],
                    )
                    batch.append({"range": f"{score_col_letter}{row_idx}", "values": [[score]]})
                    batch.append({"range": f"{reason_col_letter}{row_idx}", "values": [[reason]]})
                scored += 1
            except Exception as exc:
                logger.error("[%d/%d] %s → EXCEPTION: %s", i, len(to_score), username, exc)
                errors += 1

            time.sleep(CLAUDE_COOLDOWN)

            if not args.compare and len(batch) >= BATCH_SIZE * 2:  # *2 because each lead adds 2 entries
                flush_batch(worksheet, batch, label=f"through row {row_idx}")
                batch = []
    except KeyboardInterrupt:
        logger.warning("Interrupted — flushing %d buffered scores before exit.", len(batch) // 2)

    if not args.compare:
        flush_batch(worksheet, batch, label="final")

    logger.info(
        "Done. Scored: %d | Errors: %d | Total processed: %d",
        scored, errors, len(to_score),
    )


if __name__ == "__main__":
    main()
