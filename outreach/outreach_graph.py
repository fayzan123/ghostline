"""
outreach_graph.py — LangGraph StateGraph that wires together all outreach
agent modules into a stateful, interruptible workflow.

Nodes (in order):
  1. load_leads       — Fetch uncontacted leads from Google Sheet, slice to BATCH_SIZE.
  2. fetch_readmes    — Fetch GitHub READMEs for all leads in the batch.
  3. generate_emails  — Call Claude to generate a personalized email per lead.
  4. present_for_review — Print all drafts to the terminal for human review.
  5. process_approval — Apply human approval decisions to drafts in state.
  6. send_emails      — Send approved/edited drafts via Outlook SMTP.
  7. update_sheet     — Write back contacted/bounced/rejected status to Google Sheet.
  8. report           — Print a summary of the run to stdout.

The graph compiles with interrupt_before=["process_approval"] so that the
human reviewer can inspect emails after present_for_review and inject
approval_decisions via Command(resume=decisions) before process_approval runs.

Public API:
  build_outreach_graph() -> CompiledGraph
      Called by the entry point (run_outreach.py). NOT called at import time.
"""

import logging
from datetime import date

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from outreach.outreach_state import OutreachState, EmailDraft
from outreach.outreach_config import BATCH_SIZE, CHECKPOINT_DB
from outreach.outreach_sheets import (
    load_uncontacted_leads,
    mark_lead_contacted,
    mark_lead_bounced,
)
from outreach.readme_fetcher import fetch_readmes_batch
from outreach.email_generator import generate_emails_batch
from outreach.email_sender import send_batch
from discovery.github_client import GitHubClient
from shared.sheets import connect_to_sheet

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level GitHubClient — instantiated once and shared across invocations
# ---------------------------------------------------------------------------

_github_client = GitHubClient()

# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def load_leads(state: OutreachState) -> dict:
    """Load uncontacted leads from the Google Sheet and slice to BATCH_SIZE."""
    leads = load_uncontacted_leads()
    batch = leads[:BATCH_SIZE]

    logger.info(
        "load_leads: %d total uncontacted leads, sliced to %d for this batch.",
        len(leads),
        len(batch),
    )

    return {
        "leads": batch,
        "batch_index": state.get("batch_index", 0),
        "run_date": date.today().isoformat(),
        "errors": [],
    }


def fetch_readmes(state: OutreachState) -> dict:
    """Fetch GitHub READMEs for all leads in the current batch."""
    leads = state["leads"]
    readmes = fetch_readmes_batch(leads, _github_client)

    logger.info(
        "fetch_readmes: fetched %d READMEs (%d non-empty).",
        len(readmes),
        sum(1 for v in readmes.values() if v),
    )

    return {"readmes": readmes}


def generate_emails(state: OutreachState) -> dict:
    """Build (lead_index, lead, readme_text) tuples and generate email drafts."""
    leads = state["leads"]
    readmes = state.get("readmes", {})

    leads_with_readmes: list[tuple[int, dict, str]] = []
    for i, lead in enumerate(leads):
        # Match the lead to its README by trying repo_url slug then repo_name
        repo_name = str(lead.get("repo_name", "")).strip()
        readme_text = readmes.get(repo_name, "")

        # If not found by repo_name, try matching by repo_url-derived slug
        if not readme_text:
            from outreach.readme_fetcher import _parse_repo_slug
            slug = _parse_repo_slug(str(lead.get("repo_url", "")))
            if slug:
                readme_text = readmes.get(slug, "")

        leads_with_readmes.append((i, lead, readme_text))

    drafts = generate_emails_batch(leads_with_readmes)

    logger.info(
        "generate_emails: %d drafts generated (%d pending, %d failed).",
        len(drafts),
        sum(1 for d in drafts if d["status"] == "pending"),
        sum(1 for d in drafts if d["status"] == "failed"),
    )

    return {"drafts": drafts}


def present_for_review(state: OutreachState) -> dict:
    """Format and print all draft emails to the terminal for human review.

    This node only displays — it does not collect input. The graph interrupts
    after this node (before process_approval) so the entry point can collect
    human decisions externally.
    """
    drafts = state.get("drafts", [])
    total = len(drafts)

    print(f"\nGenerated {total} emails. Starting review...\n")

    for i, draft in enumerate(drafts, start=1):
        # Skip failed drafts in display
        if draft["status"] == "failed":
            print(f"{'=' * 54}")
            print(f"Email {i}/{total}  [FAILED — skipped]")
            print(f"{'=' * 54}")
            print(f"  Error: {draft.get('send_error', 'unknown')}\n")
            continue

        ctx = draft.get("lead_context", {})

        print(f"{'=' * 54}")
        print(f"Email {i}/{total}")
        print(f"{'=' * 54}")
        print()
        print("LEAD CONTEXT:")
        print(f"  Name:       {ctx.get('full_name', ctx.get('github_username', ''))}")
        print(f"  Username:   {ctx.get('github_username', '')}")
        print(f"  Email:      {draft.get('to_email', '')}")
        print(f"  Repo:       {ctx.get('repo_name', '')} ({ctx.get('repo_stars', 0)} stars)")
        print(f"  Frameworks: {ctx.get('frameworks_detected', '')}")
        print(f"  Score:      {ctx.get('lead_score', '')} ({ctx.get('lead_tier', '')})")
        print(f"  Company:    {ctx.get('profile_company', '') or 'Independent'}")
        print()
        print("GENERATED EMAIL:")
        print(f"  Subject: {draft['subject']}")
        print()
        # Indent body lines for visual clarity
        for line in draft["body"].splitlines():
            print(f"  {line}")
        print()

    return {}


def process_approval(state: OutreachState) -> dict:
    """Apply human approval decisions to the drafts in state.

    This node runs AFTER the human-in-the-loop interrupt. It receives
    approval_decisions from the resume command — a list of dicts with keys:
      - index: int (position in the drafts list)
      - action: str ("approve", "reject", "edit")
      - edited_body: str (non-empty only when action == "edit")

    Each decision updates the corresponding draft's status field:
      - "approve" -> status = "approved"
      - "reject"  -> status = "rejected"
      - "edit"    -> status = "edited", edited_body set
    """
    decisions = state.get("approval_decisions", [])
    drafts: list[EmailDraft] = list(state.get("drafts", []))

    # Build a lookup for fast access
    decision_map: dict[int, dict] = {d["index"]: d for d in decisions}

    updated_drafts: list[EmailDraft] = []
    for i, draft in enumerate(drafts):
        # Shallow copy so we don't mutate state in place
        updated: EmailDraft = dict(draft)  # type: ignore[assignment]

        if draft["status"] == "failed":
            # Leave failed drafts untouched
            updated_drafts.append(updated)
            continue

        decision = decision_map.get(i)
        if decision is None:
            # No decision provided — default to rejected
            updated["status"] = "rejected"
            updated_drafts.append(updated)
            continue

        action = decision.get("action", "reject").lower()

        if action == "approve":
            updated["status"] = "approved"
        elif action == "edit":
            updated["status"] = "edited"
            updated["edited_body"] = decision.get("edited_body", "")
        elif action == "quit":
            # User quit the review session — preserve as pending so a --resume
            # run will re-present these drafts for review rather than silently
            # rejecting them.
            updated["status"] = "pending"
        else:
            # "reject" or any unrecognized action
            updated["status"] = "rejected"

        updated_drafts.append(updated)

    approved_count = sum(
        1 for d in updated_drafts if d["status"] in ("approved", "edited")
    )
    rejected_count = sum(1 for d in updated_drafts if d["status"] == "rejected")

    logger.info(
        "process_approval: %d approved/edited, %d rejected.",
        approved_count,
        rejected_count,
    )

    return {"drafts": updated_drafts}


def send_emails(state: OutreachState) -> dict:
    """Send approved/edited drafts via Outlook SMTP and update state counts."""
    drafts = state.get("drafts", [])

    updated_drafts = send_batch(drafts)

    sent = sum(1 for d in updated_drafts if d["status"] == "sent")
    failed = sum(1 for d in updated_drafts if d["status"] == "failed")
    bounced = sum(1 for d in updated_drafts if d["status"] == "bounced")

    logger.info(
        "send_emails: %d sent, %d failed, %d bounced.", sent, failed, bounced
    )

    return {
        "drafts": updated_drafts,
        "sent_count": sent,
        "failed_count": failed,
        "bounced_count": bounced,
    }


def update_sheet(state: OutreachState) -> dict:
    """Write back send results to the Google Sheet.

    For each draft:
      - sent    -> mark_lead_contacted (contacted=TRUE, contacted_at, etc.)
      - bounced -> mark_lead_bounced   (response_status=bounced)
      - rejected -> note in sheet (optional, for tracking)
    """
    drafts = state.get("drafts", [])
    errors: list[str] = list(state.get("errors", []))

    _, worksheet = connect_to_sheet()

    for draft in drafts:
        ctx = draft.get("lead_context", {})
        sheet_row = ctx.get("_sheet_row")
        if not sheet_row:
            logger.warning(
                "No _sheet_row for %s — skipping sheet update.",
                draft.get("to_email", "?"),
            )
            continue

        status = draft.get("status", "")

        try:
            if status == "sent":
                notes = (
                    f"outreach_batch_{state.get('run_date', '')}, "
                    f"subject: {draft.get('subject', '')}"
                )
                mark_lead_contacted(worksheet, sheet_row, notes=notes)

            elif status == "bounced":
                notes = (
                    f"bounced: {draft.get('send_error', 'unknown')}"
                )
                mark_lead_bounced(worksheet, sheet_row, notes=notes)

            elif status == "rejected":
                # Optionally note the rejection — do not mark as contacted
                logger.debug(
                    "Row %d rejected in review — no sheet update.", sheet_row
                )

        except Exception as exc:
            error_msg = f"Sheet update failed for row {sheet_row}: {exc}"
            logger.error(error_msg)
            errors.append(error_msg)

    return {"errors": errors}


def report(state: OutreachState) -> dict:
    """Print a summary of the run to stdout."""
    sent = state.get("sent_count", 0)
    failed = state.get("failed_count", 0)
    bounced = state.get("bounced_count", 0)
    drafts = state.get("drafts", [])
    rejected = sum(1 for d in drafts if d.get("status") == "rejected")

    print()
    print("=" * 54)
    print("OUTREACH RUN SUMMARY")
    print("=" * 54)
    print(f"  Date:     {state.get('run_date', 'unknown')}")
    print(f"  Batch:    {len(drafts)} emails generated")
    print(f"  Sent:     {sent}")
    print(f"  Failed:   {failed}")
    print(f"  Bounced:  {bounced}")
    print(f"  Rejected: {rejected}")
    print("=" * 54)
    print()

    errors = state.get("errors", [])
    if errors:
        print(f"Errors ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
        print()

    return {}


# ---------------------------------------------------------------------------
# Routing functions for conditional edges
# ---------------------------------------------------------------------------


def _route_after_load(state: OutreachState) -> str:
    """Route to END if no leads were loaded, otherwise continue."""
    if not state.get("leads"):
        print("No uncontacted leads available. Run Phase 1 (run.py) to discover new leads.")
        return "end"
    return "continue"


def _route_after_approval(state: OutreachState) -> str:
    """Route to send_emails if any drafts are approved/edited, else skip to update_sheet."""
    drafts = state.get("drafts", [])
    has_sendable = any(
        d.get("status") in ("approved", "edited") for d in drafts
    )
    if has_sendable:
        return "has_approved"
    return "all_rejected"


# ---------------------------------------------------------------------------
# Graph builder — called by the entry point, NOT at import time
# ---------------------------------------------------------------------------


def build_outreach_graph():
    """Build and compile the outreach StateGraph with SQLite checkpointer.

    Returns:
        A compiled LangGraph graph ready for invocation.
    """
    graph = StateGraph(OutreachState)

    # --- Add nodes ---
    graph.add_node("load_leads", load_leads)
    graph.add_node("fetch_readmes", fetch_readmes)
    graph.add_node("generate_emails", generate_emails)
    graph.add_node("present_for_review", present_for_review)
    graph.add_node("process_approval", process_approval)
    graph.add_node("send_emails", send_emails)
    graph.add_node("update_sheet", update_sheet)
    graph.add_node("report", report)

    # --- Set entry point ---
    graph.set_entry_point("load_leads")

    # --- Edges ---

    # After load_leads: conditional — no leads -> END, else -> fetch_readmes
    graph.add_conditional_edges(
        "load_leads",
        _route_after_load,
        {
            "end": END,
            "continue": "fetch_readmes",
        },
    )

    # Linear edges through the middle of the pipeline
    graph.add_edge("fetch_readmes", "generate_emails")
    graph.add_edge("generate_emails", "present_for_review")
    graph.add_edge("present_for_review", "process_approval")

    # After process_approval: conditional — approved drafts -> send, else -> update_sheet
    graph.add_conditional_edges(
        "process_approval",
        _route_after_approval,
        {
            "has_approved": "send_emails",
            "all_rejected": "update_sheet",
        },
    )

    # Linear edges to finish
    graph.add_edge("send_emails", "update_sheet")
    graph.add_edge("update_sheet", "report")
    graph.add_edge("report", END)

    # --- Compile with checkpointer and interrupt ---
    checkpointer = SqliteSaver.from_conn_string(CHECKPOINT_DB)

    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["process_approval"],
    )

    logger.info("Outreach graph compiled with interrupt_before=['process_approval'].")

    return compiled
