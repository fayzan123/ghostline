"""
email_generator.py — Generate personalized cold emails via the Anthropic Claude API.

Loads CHOX_CONTEXT.md once at import time, instantiates a single Anthropic client,
and exposes two public functions:

    generate_email(lead, readme_text) -> EmailDraft
    generate_emails_batch(leads_with_readmes) -> list[EmailDraft]

Personalization is derived exclusively from the repo README content and metadata.
The inferred_pain_point and risk_apis_detected fields are intentionally ignored —
all leads share the same pain point, so those fields add no differentiation.

Retry logic: rate-limit errors (429) trigger exponential backoff (2s, 4s, 8s).
Parse failures return a clearly marked failure dict rather than raising.
Batch generation logs progress and never lets a single failure crash the run.
"""

import logging
import os
import re
import time
from typing import Optional

import anthropic

from outreach.outreach_config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MAX_TOKENS,
    CLAUDE_MODEL,
    CLAUDE_TEMPERATURE,
    PHYSICAL_ADDRESS,
    README_MAX_CHARS,
)
from outreach.outreach_state import EmailDraft

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load CHOX_CONTEXT.md once at import time
# ---------------------------------------------------------------------------

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_MODULE_DIR)
_CHOX_CONTEXT_PATH = os.path.join(_PROJECT_ROOT, "docs", "CHOX_CONTEXT.md")

try:
    with open(_CHOX_CONTEXT_PATH, "r", encoding="utf-8") as _f:
        _CHOX_CONTEXT = _f.read()
except FileNotFoundError:
    logger.error("CHOX_CONTEXT.md not found at %s", _CHOX_CONTEXT_PATH)
    raise RuntimeError(
        f"Cannot find docs/CHOX_CONTEXT.md at {_CHOX_CONTEXT_PATH}. "
        "This file is required for email generation."
    )

# ---------------------------------------------------------------------------
# Anthropic client — instantiated once at module level
# ---------------------------------------------------------------------------

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 2  # 2s, 4s, 8s

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = f"""\
You are a cold email copywriter for Chox, an AI agent governance layer.
You write short, personalized outreach emails to developers who are building
AI agents that call external APIs.

PRODUCT CONTEXT:
{_CHOX_CONTEXT}

EMAIL CONSTRAINTS:
- Maximum 150 words, 5-7 sentences total.
- Plain text only. No markdown formatting, no bold, no italics, no bullet points, no links (except chox.ai in the sign-off).
- Do NOT use em dashes. Use commas, periods, or parentheses instead.

STRUCTURE (three paragraphs):
- First paragraph: Reference their specific project and what it does (1-2 sentences). Personalize based on what they are building, what frameworks they use, what their agent does. This is the primary personalization vector.
- Second paragraph: Connect what they are building to Chox's core value prop — governance and visibility over agent tool calls. Keep it concrete: classify, risk-score, shadow verdicts, two-line integration. (2-3 sentences)
- Third paragraph: Low-friction CTA question (1 sentence). Ask a question, not a commitment. Never say "schedule a demo" or "book a call."

SIGN-OFF (always use this exactly):
-- Fayzan & Dilraj
Co-founders, Chox (chox.ai)

FOOTER (always include after the sign-off, separated by a blank line):
{PHYSICAL_ADDRESS}
Reply "unsubscribe" to opt out.

TONE:
- Write like a developer talking to a developer, not a marketer.
- Be specific. Mention their repo name, their framework, what they are building.
- Assume they are smart and busy. Do not over-explain concepts they already know.
- Show, don't tell. Describe what Chox does concretely, not abstractly.
- One clear value proposition per email, not a feature dump.
- No urgency tactics, no scarcity, no flattery beyond genuine project acknowledgment.

BANNED WORDS AND PATTERNS (never use any of these):
- "excited"
- "revolutionary"
- "game-changing"
- "leverage"
- "synergy"
- "cutting-edge"
- "transform"
- "unlock"
- "empower"
- "streamline"
- "robust"
- "seamless"
- "delighted"
- em dashes (the -- or \u2014 character used mid-sentence)

ADDITIONAL RULES:
- Never claim to know them personally.
- Do not mention that you read their README or scraped their data. Write as if you naturally came across their project.
- Subject line: 3-7 words, lowercase (except proper nouns), no exclamation marks, no ALL CAPS, no emojis, no "Re:" or "Fwd:" deception.

OUTPUT FORMAT (you must follow this exactly):
SUBJECT: <the subject line>
BODY:
<the full email body including sign-off and footer>
"""

# ---------------------------------------------------------------------------
# User prompt template
# ---------------------------------------------------------------------------

_USER_PROMPT_TEMPLATE = """\
Write a cold outreach email for this developer:

NAME: {name}
PROJECT: {repo_name} -- {repo_description}
README SUMMARY: {readme_summary}
FRAMEWORKS: {frameworks}
COMPANY: {company}
"""

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_SUBJECT_RE = re.compile(r"^SUBJECT:\s*(.+)$", re.MULTILINE)
_BODY_RE = re.compile(r"^BODY:\s*\n(.*)", re.DOTALL | re.MULTILINE)


def _parse_response(text: str) -> Optional[tuple[str, str]]:
    """
    Parse Claude's response into (subject, body).

    Returns None if the response does not match the expected format.
    """
    subject_match = _SUBJECT_RE.search(text)
    body_match = _BODY_RE.search(text)

    if not subject_match or not body_match:
        return None

    subject = subject_match.group(1).strip()
    body = body_match.group(1).strip()

    if not subject or not body:
        return None

    return subject, body


# ---------------------------------------------------------------------------
# Single email generation
# ---------------------------------------------------------------------------


def _build_user_prompt(lead: dict, readme_text: str) -> str:
    """Build the per-lead user prompt from lead data and README content."""
    name = (
        lead.get("full_name")
        or lead.get("github_username")
        or "there"
    )
    repo_name = lead.get("repo_name", "unknown project")
    repo_description = lead.get("repo_description", "no description available")
    frameworks = lead.get("frameworks_detected", "not specified")
    company = lead.get("profile_company") or "Independent"

    readme_summary = readme_text[:README_MAX_CHARS].strip() if readme_text else "README not available"

    return _USER_PROMPT_TEMPLATE.format(
        name=name,
        repo_name=repo_name,
        repo_description=repo_description,
        readme_summary=readme_summary,
        frameworks=frameworks,
        company=company,
    )


def _call_claude_with_retry(user_prompt: str) -> str:
    """
    Call the Anthropic API with exponential backoff on rate-limit errors.

    Returns the raw text content from Claude's response.
    Raises on non-rate-limit API errors after exhausting retries.
    """
    last_exception: Optional[Exception] = None

    for attempt in range(_MAX_RETRIES):
        try:
            response = _client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=CLAUDE_MAX_TOKENS,
                temperature=CLAUDE_TEMPERATURE,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text

        except anthropic.RateLimitError as exc:
            last_exception = exc
            wait_time = _BASE_BACKOFF_SECONDS * (2 ** attempt)
            logger.warning(
                "Rate limited by Anthropic API (attempt %d/%d). "
                "Retrying in %ds...",
                attempt + 1,
                _MAX_RETRIES,
                wait_time,
            )
            time.sleep(wait_time)

        except anthropic.APIError as exc:
            # Non-rate-limit API errors: do not retry, raise immediately.
            logger.error("Anthropic API error: %s", exc)
            raise

    # Exhausted all retries on rate limiting.
    raise last_exception  # type: ignore[misc]


def _make_failure_draft(
    lead: dict,
    lead_index: int,
    readme_text: str,
    error_msg: str,
) -> EmailDraft:
    """Return an EmailDraft marked as failed with a descriptive error."""
    return EmailDraft(
        lead_index=lead_index,
        to_email=lead.get("email", ""),
        to_name=lead.get("full_name") or lead.get("github_username", ""),
        subject="",
        body="",
        lead_context=lead,
        readme_snippet=(readme_text or "")[:500],
        status="failed",
        edited_body="",
        send_error=error_msg,
    )


def generate_email(
    lead: dict,
    readme_text: str,
    lead_index: int = 0,
) -> EmailDraft:
    """
    Generate a single personalized cold email for a lead.

    Args:
        lead: Lead row dict from the Google Sheet.
        readme_text: Raw README content (will be truncated internally).
        lead_index: Position in the leads list (for state tracking).

    Returns:
        An EmailDraft dict. On success, status is "pending" and subject/body
        are populated. On failure, status is "failed" and send_error describes
        what went wrong.
    """
    to_name = lead.get("full_name") or lead.get("github_username", "")
    to_email = lead.get("email", "")
    readme_snippet = (readme_text or "")[:500]

    # --- Call Claude ---
    user_prompt = _build_user_prompt(lead, readme_text)

    try:
        raw_response = _call_claude_with_retry(user_prompt)
    except Exception as exc:
        error_msg = f"Claude API call failed: {exc}"
        logger.error(
            "Email generation failed for %s (%s): %s",
            to_name,
            lead.get("repo_name", "?"),
            error_msg,
        )
        return _make_failure_draft(lead, lead_index, readme_text, error_msg)

    # --- Parse response ---
    parsed = _parse_response(raw_response)

    if parsed is None:
        error_msg = (
            "malformed_generation: Claude response did not match "
            "expected SUBJECT/BODY format"
        )
        logger.warning(
            "Parse failure for %s (%s). Raw response (first 300 chars): %s",
            to_name,
            lead.get("repo_name", "?"),
            raw_response[:300],
        )
        return _make_failure_draft(lead, lead_index, readme_text, error_msg)

    subject, body = parsed

    # --- Validate subject length ---
    if len(subject) > 80:
        subject = subject[:77] + "..."
        logger.info("Truncated subject line for %s to 80 chars.", to_name)

    return EmailDraft(
        lead_index=lead_index,
        to_email=to_email,
        to_name=to_name,
        subject=subject,
        body=body,
        lead_context=lead,
        readme_snippet=readme_snippet,
        status="pending",
        edited_body="",
        send_error="",
    )


# ---------------------------------------------------------------------------
# Batch email generation
# ---------------------------------------------------------------------------


def generate_emails_batch(
    leads_with_readmes: list[tuple[int, dict, str]],
) -> list[EmailDraft]:
    """
    Generate emails for a batch of leads. Never lets one failure crash the rest.

    Args:
        leads_with_readmes: List of (lead_index, lead_dict, readme_text) tuples.

    Returns:
        List of EmailDraft dicts, one per input lead. Failed generations have
        status="failed" with a descriptive send_error.
    """
    drafts: list[EmailDraft] = []
    total = len(leads_with_readmes)

    for i, (lead_index, lead, readme_text) in enumerate(leads_with_readmes, start=1):
        lead_name = lead.get("full_name") or lead.get("github_username", "?")
        repo_name = lead.get("repo_name", "?")

        logger.info(
            "Generating email %d/%d for %s (%s)...",
            i,
            total,
            lead_name,
            repo_name,
        )

        draft = generate_email(lead, readme_text, lead_index=lead_index)
        drafts.append(draft)

        if draft["status"] == "failed":
            logger.warning(
                "  -> FAILED: %s",
                draft["send_error"],
            )
        else:
            logger.info(
                "  -> OK: subject=%r (%d words in body)",
                draft["subject"],
                len(draft["body"].split()),
            )

    # --- Summary ---
    succeeded = sum(1 for d in drafts if d["status"] == "pending")
    failed = sum(1 for d in drafts if d["status"] == "failed")
    logger.info(
        "Batch generation complete: %d succeeded, %d failed out of %d total.",
        succeeded,
        failed,
        total,
    )

    return drafts
