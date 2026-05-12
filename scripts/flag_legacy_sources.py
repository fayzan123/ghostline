#!/usr/bin/env python3
"""
flag_legacy_sources.py — One-off remediation script.

Email extraction used to draw from four sources: GitHub profile email,
commit author metadata, public PushEvent payloads, and profile bio.
The commit and PushEvent paths were removed because they violate the
GitHub Acceptable Use Policy clause on using scraped information for
unsolicited email. This script walks every row in the Google Sheet and
flags rows whose email was sourced via the removed paths so they are
never contacted by future outreach runs.

Behavior, per row:
  - Reads the email_source column.
  - If the source is one of the legacy values (commits, events, or any
    value other than profile / bio / empty), the row is flagged.
  - For flagged rows that have NOT yet been contacted, response_status
    is set to "suppressed_legacy_source" (the outreach loader skips this
    value) and a dated note is appended to the notes column.
  - For flagged rows that have already been contacted, only a note is
    appended. We do not rewrite the historical contact state.

Run with --dry-run first to preview. Run without flags to actually write.

Usage:
    python scripts/flag_legacy_sources.py --dry-run
    python scripts/flag_legacy_sources.py
"""

import argparse
import logging
import os
import sys
import time
from datetime import date

# Allow running as `python scripts/flag_legacy_sources.py` from project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.sheets import connect_to_sheet  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Sources we now consider consent-based and acceptable.
ALLOWED_SOURCES = {"profile", "bio", ""}

# Column indices (1-indexed) — must match shared/config.GOOGLE_SHEET_HEADERS.
_COL_RESPONSE_STATUS = 26  # Z
_COL_NOTES = 27            # AA

_SHEETS_COOLDOWN = 1.5     # seconds between writes to stay under quota


def _col_to_a1(col: int) -> str:
    result = ""
    while col > 0:
        col, remainder = divmod(col - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _cell(col: int, row: int) -> str:
    return f"{_col_to_a1(col)}{row}"


def _append_note(existing: str, addition: str) -> str:
    existing = (existing or "").strip()
    if not existing:
        return addition
    if addition in existing:
        return existing
    return f"{existing}; {addition}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing to the sheet.",
    )
    args = parser.parse_args()

    _, worksheet = connect_to_sheet()
    rows = worksheet.get_all_records()
    logger.info("Loaded %d data rows.", len(rows))

    today = date.today().isoformat()
    note_text = (
        f"flagged {today}: email sourced via legacy method, "
        "suppressed under GitHub AUP cleanup"
    )

    suppressed = 0       # rows we will / would suppress
    annotated_only = 0   # already-contacted rows: note-only
    skipped_clean = 0    # rows on an allowed source
    by_source: dict[str, int] = {}

    for idx, record in enumerate(rows):
        sheet_row = idx + 2  # row 1 is the header
        source = str(record.get("email_source", "")).strip().lower()
        by_source[source or "(empty)"] = by_source.get(source or "(empty)", 0) + 1

        if source in ALLOWED_SOURCES:
            skipped_clean += 1
            continue

        contacted = str(record.get("contacted", "")).strip().upper() == "TRUE"
        current_status = str(record.get("response_status", "")).strip().lower()
        current_notes = str(record.get("notes", ""))
        new_notes = _append_note(current_notes, note_text)

        username = record.get("github_username", "?")

        if contacted:
            annotated_only += 1
            logger.info(
                "[contacted] %s (row %d, source=%s) — note only",
                username,
                sheet_row,
                source,
            )
            if not args.dry_run:
                worksheet.update_acell(_cell(_COL_NOTES, sheet_row), new_notes)
                time.sleep(_SHEETS_COOLDOWN)
            continue

        suppressed += 1
        logger.info(
            "[suppress]  %s (row %d, source=%s) — set response_status + note",
            username,
            sheet_row,
            source,
        )

        if args.dry_run:
            continue

        # Two single-cell updates per row. Could be batched with batch_update
        # for speed, but this script runs once and we prefer the simple path.
        if current_status not in ("suppressed_legacy_source",):
            worksheet.update_acell(
                _cell(_COL_RESPONSE_STATUS, sheet_row),
                "suppressed_legacy_source",
            )
            time.sleep(_SHEETS_COOLDOWN)
        worksheet.update_acell(_cell(_COL_NOTES, sheet_row), new_notes)
        time.sleep(_SHEETS_COOLDOWN)

    logger.info("--- Source breakdown ---")
    for src, count in sorted(by_source.items(), key=lambda kv: -kv[1]):
        marker = "OK " if src in ALLOWED_SOURCES or src == "(empty)" else "FLG"
        logger.info("  %s %-12s %d", marker, src, count)

    logger.info("--- Summary ---")
    logger.info("  Clean (profile / bio / empty): %d", skipped_clean)
    logger.info("  Flagged + suppressed (uncontacted): %d", suppressed)
    logger.info("  Flagged + annotated only (already contacted): %d", annotated_only)
    if args.dry_run:
        logger.info("DRY RUN — no changes written.")
    else:
        logger.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
