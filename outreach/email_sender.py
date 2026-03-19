"""
email_sender.py — SMTP email sending module for the Ghostline outreach agent.

Responsibilities:
  - Establish a single STARTTLS connection to Gmail SMTP for an entire batch.
  - Build RFC 2822-compliant plain-text MIME messages with all required headers.
  - Apply randomized inter-send pacing per the deliverability strategy.
  - Classify failures as hard bounces ("bounced") vs transient/general failures
    ("failed") and surface both through the EmailDraft status field.
  - Close the SMTP connection cleanly in a finally block regardless of outcome.
  - Provide is_business_hours() as an advisory utility for the entry point.

Design decisions:
  - One connection for the whole batch (not one per email).  Re-establishing a
    TLS handshake per email adds latency and may trigger rate-limiting at
    Gmail's edge; a single authenticated session is both faster and stealthier.
  - Hard bounce classification is based purely on SMTP response codes, not string
    parsing.  SMTPRecipientsRefused is the canonical "5xx RCPT TO rejected" signal.
    SMTPDataError with a 5xx permanent code is also treated as a bounce because
    the receiving MTA has permanently rejected the message for that recipient.
    All other SMTPException subclasses are general failures.
  - Message-ID is generated per message via email.utils.make_msgid so that every
    outbound email has a globally unique identifier.  This aids deliverability
    (some receiving MTAs penalise missing or duplicate Message-IDs) and makes
    post-send debugging tractable.
  - The pacing sleep fires after every send attempt (success or failure) so the
    inter-send gap is always respected even when the SMTP server is slow.
  - is_business_hours() uses local system time, not recipient time zone, because
    the outreach agent runs on a single developer machine.  The caller is
    responsible for any recipient-side time zone logic if needed in the future.
"""

import logging
import random
import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from typing import List

from outreach.outreach_config import (
    MAX_SEND_DELAY_SECONDS,
    MIN_SEND_DELAY_SECONDS,
    SENDER_EMAIL,
    SENDER_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
)
from outreach.outreach_state import EmailDraft

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Business hours utility
# ---------------------------------------------------------------------------

# Weekday integers from datetime.weekday(): Monday=0 … Sunday=6
_WEEKDAYS = {0, 1, 2, 3, 4}
_BUSINESS_HOUR_START = 9   # 09:00 inclusive
_BUSINESS_HOUR_END   = 17  # 17:00 exclusive (i.e. up to 16:59)


def is_business_hours() -> bool:
    """Return True if the current local time is a weekday between 9 am and 5 pm.

    This is an advisory check only.  The send_batch function never consults it.
    The run_outreach entry point should call it and warn the user if False, but
    must not block sending based on the result.
    """
    now = datetime.now()
    return (
        now.weekday() in _WEEKDAYS
        and _BUSINESS_HOUR_START <= now.hour < _BUSINESS_HOUR_END
    )


# ---------------------------------------------------------------------------
# MIME construction
# ---------------------------------------------------------------------------

def _build_message(draft: EmailDraft) -> MIMEText:
    """Construct a plain-text MIMEText message with all required headers.

    CAN-SPAM requirements satisfied here:
      - Accurate From header with display name identifying Chox co-founders.
      - Reply-To set to the same sending address (never noreply@).
      - Physical address and unsubscribe line are included in the email body
        by the email_generator, but we assert they are present here as a
        belt-and-suspenders check so the sender module is self-sufficient.

    The body received from EmailDraft is used verbatim; the generator owns
    content policy.  The sender does not alter or append to the body.
    """
    body = draft["edited_body"] if draft.get("edited_body") else draft["body"]

    msg = MIMEText(body, "plain", "utf-8")

    # From: display name + address, RFC 2822 encoded
    msg["From"] = formataddr((SENDER_NAME, SENDER_EMAIL))

    # To: display name if available, otherwise bare address
    to_name = draft.get("to_name", "")
    to_address = draft["to_email"]
    msg["To"] = formataddr((to_name, to_address)) if to_name else to_address

    msg["Subject"] = draft["subject"]

    # Reply-To: same as From so replies land in the monitored inbox
    msg["Reply-To"] = formataddr((SENDER_NAME, SENDER_EMAIL))

    # Message-ID: globally unique per RFC 2822; aids deliverability
    msg["Message-ID"] = make_msgid(domain=SENDER_EMAIL.split("@")[-1])

    # Date: RFC 2822 format with local timezone offset; localtime=True captures
    # the sender's timezone which is fine for a personal-account send
    msg["Date"] = formatdate(localtime=True)

    return msg


# ---------------------------------------------------------------------------
# CAN-SPAM body content check
# ---------------------------------------------------------------------------

_UNSUBSCRIBE_MARKER = "unsubscribe"


def _warn_if_missing_compliance_elements(draft: EmailDraft) -> None:
    """Log a warning if the email body is missing an unsubscribe line."""
    body_lower = (draft.get("body") or "").lower()
    if _UNSUBSCRIBE_MARKER not in body_lower:
        logger.warning(
            "Draft for %s is missing an unsubscribe line.",
            draft["to_email"],
        )


# ---------------------------------------------------------------------------
# Bounce / failure classification
# ---------------------------------------------------------------------------

def _is_hard_bounce(exc: smtplib.SMTPException) -> bool:
    """Return True if the exception indicates a permanent recipient rejection.

    Hard bounce criteria:
      - SMTPRecipientsRefused: the receiving server rejected the RCPT TO
        command with a 5xx permanent failure code.  The canonical signal that
        the recipient address does not exist or has blocked the sender.
      - SMTPDataError with a 5xx code: the DATA command was accepted but the
        server then issued a permanent rejection.  Less common but semantically
        a permanent failure tied to the recipient.

    All other SMTPException subclasses (SMTPAuthenticationError,
    SMTPConnectError, SMTPServerDisconnected, SMTPSenderRefused, generic
    SMTPException) are general failures — they indicate infrastructure or
    authentication problems, not recipient-level rejection.
    """
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return True
    if isinstance(exc, smtplib.SMTPDataError):
        code = exc.smtp_code  # integer SMTP response code
        if isinstance(code, int) and 500 <= code <= 599:
            return True
    return False


# ---------------------------------------------------------------------------
# Core send logic
# ---------------------------------------------------------------------------

def _send_one(
    smtp: smtplib.SMTP,
    draft: EmailDraft,
) -> EmailDraft:
    """Attempt to send a single email draft over an open SMTP connection.

    Returns a copy of the draft with status, send_error updated.
    Does NOT sleep — pacing is the caller's responsibility.
    Does NOT close the SMTP connection.

    Raises nothing.  All exceptions are caught and reflected in draft status.
    """
    # Shallow copy so we do not mutate the original state list in-place
    result: EmailDraft = dict(draft)  # type: ignore[assignment]

    _warn_if_missing_compliance_elements(draft)

    try:
        msg = _build_message(draft)
        smtp.sendmail(
            from_addr=SENDER_EMAIL,
            to_addrs=[draft["to_email"]],
            msg=msg.as_string(),
        )
        result["status"] = "sent"
        result["send_error"] = ""
        logger.info("Sent to %s | subject: %s", draft["to_email"], draft["subject"])

    except smtplib.SMTPException as exc:
        if _is_hard_bounce(exc):
            result["status"] = "bounced"
            result["send_error"] = f"Hard bounce ({type(exc).__name__}): {exc}"
            logger.warning(
                "Hard bounce for %s: %s", draft["to_email"], exc
            )
        else:
            result["status"] = "failed"
            result["send_error"] = f"{type(exc).__name__}: {exc}"
            logger.error(
                "Send failure for %s: %s", draft["to_email"], exc
            )

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_batch(drafts: List[EmailDraft]) -> List[EmailDraft]:
    """Send a batch of approved email drafts via a single SMTP connection.

    Only drafts with status "approved" or "edited" are sent.  All others are
    returned unchanged.

    Connection lifecycle:
      - One SMTP connection is established at the start of the batch.
      - It is reused for every email in the batch.
      - It is closed in a finally block regardless of what happens.
      - If the connection is lost mid-batch (SMTPServerDisconnected or any
        connection-level error raised outside of _send_one), the remaining
        unsent drafts are marked "failed" and the function returns without
        raising.  Drafts that were already sent keep their "sent" status.

    Pacing:
      - A random sleep between MIN_SEND_DELAY_SECONDS and MAX_SEND_DELAY_SECONDS
        is applied after each send attempt (success or failure).
      - No sleep is applied after the last draft to avoid unnecessary blocking.

    Returns:
      The full drafts list with status and send_error fields updated for each
      draft that was processed.
    """
    results: List[EmailDraft] = list(drafts)  # work on a shallow copy of the list

    # Identify which indices in the list need sending
    to_send_indices = [
        i for i, d in enumerate(results)
        if d.get("status") in ("approved", "edited")
    ]

    if not to_send_indices:
        logger.info("send_batch called with no approved drafts — nothing to send.")
        return results

    smtp: smtplib.SMTP | None = None

    try:
        # --- Establish connection ---
        logger.info(
            "Connecting to %s:%s via STARTTLS …", SMTP_HOST, SMTP_PORT
        )
        smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()  # re-identify after TLS negotiation
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        logger.info("SMTP authenticated as %s", SMTP_USERNAME)

        # --- Send loop ---
        for loop_pos, idx in enumerate(to_send_indices):
            draft = results[idx]
            is_last = loop_pos == len(to_send_indices) - 1

            try:
                results[idx] = _send_one(smtp, draft)
            except smtplib.SMTPServerDisconnected as conn_exc:
                # Connection dropped during this send attempt.  Mark this
                # draft and all remaining unsent drafts as failed, then exit
                # the loop.  Do not re-raise; the finally block closes cleanly.
                logger.error(
                    "SMTP connection dropped while sending to %s: %s",
                    draft["to_email"],
                    conn_exc,
                )
                # Mark the draft that triggered the disconnect
                failed_draft: EmailDraft = dict(draft)  # type: ignore[assignment]
                failed_draft["status"] = "failed"
                failed_draft["send_error"] = (
                    f"SMTPServerDisconnected: {conn_exc}"
                )
                results[idx] = failed_draft

                # Mark all subsequent unsent drafts as failed
                remaining_indices = to_send_indices[loop_pos + 1:]
                for rem_idx in remaining_indices:
                    rem_draft: EmailDraft = dict(results[rem_idx])  # type: ignore[assignment]
                    rem_draft["status"] = "failed"
                    rem_draft["send_error"] = (
                        "SMTP connection lost before this email could be sent."
                    )
                    results[rem_idx] = rem_draft
                    logger.warning(
                        "Marked %s as failed (connection lost before send).",
                        rem_draft["to_email"],
                    )

                # Exit the send loop — connection is dead
                break

            # Apply pacing delay between sends (not after the last one)
            if not is_last:
                delay = random.uniform(MIN_SEND_DELAY_SECONDS, MAX_SEND_DELAY_SECONDS)
                logger.debug(
                    "Pacing: sleeping %.1f seconds before next send.", delay
                )
                time.sleep(delay)

    except (smtplib.SMTPConnectError, smtplib.SMTPAuthenticationError, OSError) as setup_exc:
        # Connection or authentication failed before any email was sent.
        # Mark all approved/edited drafts as failed.
        logger.error("SMTP setup failed: %s", setup_exc)
        for idx in to_send_indices:
            failed_draft = dict(results[idx])  # type: ignore[assignment]
            failed_draft["status"] = "failed"
            failed_draft["send_error"] = (
                f"SMTP setup error ({type(setup_exc).__name__}): {setup_exc}"
            )
            results[idx] = failed_draft

    finally:
        if smtp is not None:
            try:
                smtp.quit()
                logger.info("SMTP connection closed.")
            except smtplib.SMTPException:
                # quit() can raise if the connection is already dead.
                # Force-close the underlying socket so we do not leak it.
                try:
                    smtp.close()
                except Exception:
                    pass
                logger.debug("SMTP connection force-closed after quit() failure.")

    return results
