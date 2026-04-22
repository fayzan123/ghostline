#!/usr/bin/env python3
"""
Ghostline Outreach Agent
Run: python run_outreach.py [--dry-run] [--batch-size N] [--resume]

Orchestrates the full outreach pipeline:
  1. Validate critical config (Anthropic API key)
  2. Build the LangGraph outreach graph
  3. Invoke (fresh or resumed from checkpoint)
  4. Collect human review decisions via the terminal CLI
  5. Resume the graph with decisions injected via Command(update={"approval_decisions": decisions})
  6. Display approved emails for manual copy/paste sending
  7. Mark the spreadsheet on completion

Flags:
  --dry-run       Run through review but skip actual sending.  Prints a summary
                  of what would be sent and exits after review.
  --batch-size N  Override the BATCH_SIZE constant from outreach_config.py.
  --resume        Load from the SQLite checkpoint instead of running fresh.
                  Passes None as input so LangGraph loads state from the db.
"""

import argparse
import logging
import sys
import traceback
from datetime import date

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config validation — must happen before any outreach module is imported
# ---------------------------------------------------------------------------

def _validate_config() -> None:
    """Import outreach_config and let its module-level validation run.

    outreach_config raises RuntimeError at import time if ANTHROPIC_API_KEY
    is missing.  We catch that here and re-raise as a clean SystemExit so
    the user sees a readable message rather than a raw traceback.

    Must be called before build_outreach_graph() or any other outreach import
    that transitively imports outreach_config.
    """
    try:
        import outreach.config  # noqa: F401 — import for side-effects
    except RuntimeError as exc:
        print(f"\nConfiguration error: {exc}", file=sys.stderr)
        print(
            "\nAdd the missing variable(s) to your .env file, then re-run.",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ghostline outreach agent — generate, review, and display emails for manual sending.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python run_outreach.py                 # fresh run\n"
            "  python run_outreach.py --dry-run       # review without marking sheet\n"
            "  python run_outreach.py --resume        # resume from checkpoint\n"
            "  python run_outreach.py --batch-size 5  # use 5 leads instead of 10\n"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help=(
            "Run through review but skip actual sending. "
            "Prints a summary of approved emails and exits."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        metavar="N",
        help="Override BATCH_SIZE from outreach_config.py.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help=(
            "Load from the SQLite checkpoint (ghostline_outreach.db) instead "
            "of running a fresh pipeline.  Use this after a --quit or "
            "Ctrl-C to continue where you left off."
        ),
    )
    return parser.parse_args()



# ---------------------------------------------------------------------------
# Initial state factory
# ---------------------------------------------------------------------------

def _initial_state(batch_size_override: int | None = None) -> dict:
    """Return a clean OutreachState dict with all fields at zero values.

    If batch_size_override is provided it is stored in the state via an
    override to BATCH_SIZE so load_leads slices to the right number.
    """
    return {
        "leads": [],
        "batch_index": 0,
        "readmes": {},
        "drafts": [],
        "approval_decisions": [],
        "sent_count": 0,
        "failed_count": 0,
        "bounced_count": 0,
        "daily_send_count": 0,
        "run_date": date.today().isoformat(),
        "errors": [],
    }


# ---------------------------------------------------------------------------
# Dry-run summary printer
# ---------------------------------------------------------------------------

def _print_dry_run_summary(decisions: list, drafts: list) -> None:
    """Print what would be sent in a real run, without actually sending."""
    approved = [
        d for d in decisions
        if d.get("action") in ("approve", "edit")
    ]
    rejected = [d for d in decisions if d.get("action") == "reject"]
    quit_decisions = [d for d in decisions if d.get("action") == "quit"]

    print()
    print("=" * 54)
    print("DRY RUN SUMMARY — nothing was sent")
    print("=" * 54)
    print(f"  Would send:  {len(approved)}")
    print(f"  Rejected:    {len(rejected)}")
    print(f"  Quit/unseen: {len(quit_decisions)}")
    print()

    if approved:
        print("Emails that would be sent:")
        for dec in approved:
            idx = dec["index"]
            if idx < len(drafts):
                draft = drafts[idx]
                action_label = "edited" if dec["action"] == "edit" else "approved"
                print(
                    f"  [{action_label}] "
                    f"{draft.get('to_email', '?')} — "
                    f"{draft.get('subject', '?')}"
                )

    print("=" * 54)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # ------------------------------------------------------------------
    # Logging setup (matches run.py pattern)
    # ------------------------------------------------------------------
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = _parse_args()

    # ------------------------------------------------------------------
    # STEP 1: Validate critical config before importing anything else
    # ------------------------------------------------------------------
    logger.info("=" * 54)
    logger.info("STEP 1: VALIDATE CONFIG")
    logger.info("=" * 54)

    _validate_config()

    # Late imports — safe to do now that config is validated
    import outreach.config as outreach_config
    from outreach.graph import build_outreach_graph
    from outreach.review_cli import review_batch
    from langgraph.types import Command

    # Apply --batch-size override before build_outreach_graph() is called so
    # that load_leads reads the patched value when the graph runs.
    if args.batch_size is not None:
        if args.batch_size < 1:
            print(
                f"Error: --batch-size must be at least 1, got {args.batch_size}",
                file=sys.stderr,
            )
            sys.exit(1)
        logger.info(
            "Overriding BATCH_SIZE: %d -> %d",
            outreach_config.BATCH_SIZE,
            args.batch_size,
        )
        outreach_config.BATCH_SIZE = args.batch_size

    if args.dry_run:
        print("\n  [DRY RUN] Emails will be generated and reviewed but not marked in the sheet.\n")

    # ------------------------------------------------------------------
    # STEP 2: Build the graph
    # ------------------------------------------------------------------
    logger.info("=" * 54)
    logger.info("STEP 2: BUILD OUTREACH GRAPH")
    logger.info("=" * 54)

    graph = build_outreach_graph()

    # Thread config — keyed to today's date so each calendar day has its own
    # checkpoint thread.  --resume loads from this same thread.
    today_str = date.today().isoformat()
    thread_config = {"configurable": {"thread_id": f"outreach-{today_str}"}}

    # ------------------------------------------------------------------
    # STEP 3: Invoke the graph (fresh or resumed from checkpoint)
    # ------------------------------------------------------------------
    logger.info("=" * 54)
    logger.info("STEP 3: RUN PIPELINE%s", " (RESUME)" if args.resume else "")
    logger.info("=" * 54)

    try:
        if args.resume:
            logger.info(
                "Resuming from checkpoint thread: outreach-%s", today_str
            )
            # Use get_state() to retrieve the saved snapshot without executing
            # any nodes. graph.invoke(None) would bypass the interrupt and run
            # process_approval immediately with empty decisions.
            state_snapshot = graph.get_state(thread_config)
            if not state_snapshot or not state_snapshot.values:
                print(
                    "\nNo checkpoint found for today's thread "
                    f"(outreach-{today_str}).\n"
                    "Run without --resume to start a fresh pipeline."
                )
                sys.exit(1)
            if "process_approval" not in (state_snapshot.next or []):
                print(
                    "\nCheckpoint is not paused at the review step. "
                    "The run for today may already be complete.\n"
                    "Delete the checkpoint DB or run tomorrow for a fresh run."
                )
                sys.exit(0)
            snapshot = state_snapshot.values
        else:
            initial_state = _initial_state(
                batch_size_override=args.batch_size,
            )
            logger.info(
                "Starting fresh run for %s (batch_size=%d).",
                today_str,
                outreach_config.BATCH_SIZE,
            )
            snapshot = graph.invoke(initial_state, config=thread_config)

    except KeyboardInterrupt:
        print(
            "\n\nInterrupted before review. State saved.\n"
            "Resume with: python run_outreach.py --resume"
        )
        sys.exit(0)

    # ------------------------------------------------------------------
    # STEP 4: Collect human review decisions
    # ------------------------------------------------------------------
    logger.info("=" * 54)
    logger.info("STEP 4: HUMAN REVIEW")
    logger.info("=" * 54)

    drafts = snapshot.get("drafts", [])

    if not drafts:
        print(
            "\nNo email drafts found in graph state. "
            "The pipeline may have exited early (no leads) or the checkpoint "
            "is from a completed run.\n"
        )
        sys.exit(0)

    try:
        decisions = review_batch(drafts)
    except KeyboardInterrupt:
        print(
            "\n\nReview interrupted. State saved to checkpoint.\n"
            "Resume with: python run_outreach.py --resume"
        )
        sys.exit(0)

    # ------------------------------------------------------------------
    # STEP 5: Dry-run exit or resume graph with decisions
    # ------------------------------------------------------------------
    if args.dry_run:
        _print_dry_run_summary(decisions, drafts)
        print(
            "Dry run complete. "
            "Re-run without --dry-run to display emails and update the sheet."
        )
        sys.exit(0)

    logger.info("=" * 54)
    logger.info("STEP 5: RESUME GRAPH WITH DECISIONS")
    logger.info("=" * 54)

    approved_count = sum(
        1 for d in decisions if d.get("action") in ("approve", "edit")
    )
    quit_count = sum(1 for d in decisions if d.get("action") == "quit")

    if quit_count > 0:
        # User pressed Q — discard all decisions, save checkpoint as-is
        print(
            "\nQuit during review. No emails sent. State saved to checkpoint.\n"
            "Resume with: python run_outreach.py --resume"
        )
        sys.exit(0)

    logger.info(
        "Resuming graph with %d decision(s) (%d approved/edited).",
        len(decisions),
        approved_count,
    )

    try:
        # Command(update=...) patches the checkpoint state before resuming so
        # process_approval receives the decisions via state["approval_decisions"].
        # Command(resume=...) only delivers a value to a node that called
        # interrupt() internally — it does NOT update any state key.
        graph.invoke(
            Command(update={"approval_decisions": decisions}),
            config=thread_config,
        )
    except KeyboardInterrupt:
        print(
            "\n\nInterrupted during send. State saved.\n"
            "Resume with: python run_outreach.py --resume"
        )
        sys.exit(0)
    except Exception:
        logger.error(
            "Graph failed during send/update:\n%s", traceback.format_exc()
        )
        sys.exit(1)

    logger.info("Outreach run complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
