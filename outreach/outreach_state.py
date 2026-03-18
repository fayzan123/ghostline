"""
outreach_state.py — LangGraph state schema for the Ghostline outreach agent.

No project imports. Stdlib typing only.
Field names and types match Section 9 of OUTREACH_AGENT_PLAN.md exactly.
"""

from typing import TypedDict, Literal


class EmailDraft(TypedDict):
    lead_index: int                    # Index into the leads list
    to_email: str
    to_name: str
    subject: str
    body: str
    lead_context: dict                 # Full lead row data for review display
    readme_snippet: str                # First 500 chars of README for review
    status: Literal["pending", "approved", "rejected", "edited", "sent", "failed", "bounced"]
    edited_body: str                   # Non-empty if human edited the email
    send_error: str                    # Error message if send failed


class OutreachState(TypedDict):
    # Input data
    leads: list[dict]                  # Lead rows from Google Sheet
    batch_index: int                   # Current batch number (0-indexed)

    # README fetch results
    readmes: dict[str, str]            # repo_full_name -> README text

    # Generated emails
    drafts: list[EmailDraft]           # One per lead in current batch

    # Human review results
    approval_decisions: list[dict]     # [{index, action, edited_body}]

    # Send results
    sent_count: int
    failed_count: int
    bounced_count: int

    # Run metadata
    daily_send_count: int              # Tracks total sent today (across batches)
    run_date: str                      # ISO date string
    errors: list[str]                  # Accumulated error messages
